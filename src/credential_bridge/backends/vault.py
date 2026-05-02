"""HashiCorp Vault backend for credential-bridge."""

import logging
import os
from typing import Any, Dict, List, Optional, Union

import hvac
import requests
import urllib3

from credential_bridge.backends.base import BaseSecretBackend
from credential_bridge.exceptions import (
    ConfigurationError,
    VaultAuthError,
    VaultConnectionError,
    VaultError,
)
from credential_bridge.utils import get_session, load_config, save_config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


# Minimal LogLevel shim so callers can pass log_level without pylogshield.
class LogLevel:
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class VaultBackend(BaseSecretBackend):
    """HashiCorp Vault KV-v2 secret backend."""

    backend_name: str = "vault"

    def __init__(
        self,
        vault_url: Optional[str] = None,
        vault_token: Optional[str] = None,
        vault_role_id: Optional[str] = None,
        vault_secret_id: Optional[str] = None,
        service_name: str = "default_service",
        mount_point: str = "secret",
        proxies: Optional[Dict[str, str]] = None,
        cert: Optional[str] = None,
        log_level: Union[int, str] = logging.WARNING,
        logger: Optional[logging.Logger] = None,
        mask: bool = True,
    ) -> None:
        self.mask = mask
        self.service_name = service_name
        self.mount_point = mount_point
        self.cert = cert if cert else False
        self.proxies = proxies
        self._logger = logger or logging.getLogger(__name__)

        # Configure log level when we own the logger
        if not logger:
            self._logger.setLevel(log_level)

        self.session = get_session(cert, proxies)

        config = load_config()

        # --- Resolve vault address ---
        if vault_url:
            self.vault_addr = vault_url
        else:
            self.vault_addr = os.environ.get("VAULT_ADDR") or config.get("vault_addr")

        if not self.vault_addr:
            raise ConfigurationError(
                "Vault address must be provided via the vault_url argument, "
                "the VAULT_ADDR environment variable, or ~/.vault_config.json"
            )

        # --- Resolve credentials (args override config) ---
        self.vault_token = vault_token or config.get("vault_token")
        self.vault_role_id = vault_role_id or config.get("vault_role_id")
        self.vault_secret_id = vault_secret_id or config.get("vault_secret_id")

        # Token and AppRole are mutually exclusive
        if self.vault_token and (self.vault_role_id or self.vault_secret_id):
            raise ConfigurationError(
                "Provide either a Vault token or AppRole credentials, not both."
            )

        # At least one auth method must be present
        if not self.vault_token and not (self.vault_role_id and self.vault_secret_id):
            raise ConfigurationError(
                "No authentication method provided. Please provide either a token "
                "or AppRole credentials."
            )

        # --- Persist credentials to config ---
        if vault_token:
            config["vault_token"] = vault_token
            config["vault_role_id"] = None
            config["vault_secret_id"] = None
        elif vault_role_id and vault_secret_id:
            config["vault_role_id"] = vault_role_id
            config["vault_secret_id"] = vault_secret_id
            config["vault_token"] = None

        if vault_url:
            config["vault_addr"] = vault_url

        save_config(config)

        self.client = self._authenticate()

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _authenticate(self) -> hvac.Client:
        """Authenticate with Vault using a token or AppRole credentials."""
        self._logger.info("Authenticating with Vault...")
        try:
            if self.vault_token:
                client = hvac.Client(
                    url=self.vault_addr,
                    token=self.vault_token,
                    session=self.session,
                    verify=self.cert,
                )
                if not client.is_authenticated():
                    raise VaultAuthError(
                        "Failed to authenticate with Vault using token."
                    )
                self._logger.info("Authenticated with Vault via token.")
                return client

            # AppRole
            client = hvac.Client(
                url=self.vault_addr,
                session=self.session,
                verify=self.cert,
            )
            auth_response = client.auth.approle.login(
                role_id=self.vault_role_id,
                secret_id=self.vault_secret_id,
            )
            if "auth" not in auth_response or "client_token" not in auth_response["auth"]:
                raise VaultAuthError(
                    "Failed to authenticate with Vault using AppRole."
                )
            client.token = auth_response["auth"]["client_token"]
            self._logger.info("Authenticated with Vault via AppRole.")
            return client

        except VaultAuthError:
            raise
        except VaultConnectionError:
            raise
        except hvac.exceptions.Forbidden as exc:
            raise VaultAuthError(f"Forbidden: {exc}") from exc
        except hvac.exceptions.InvalidRequest as exc:
            raise VaultAuthError(f"Invalid request: {exc}") from exc
        except (hvac.exceptions.VaultDown, requests.ConnectionError, requests.Timeout) as exc:
            raise VaultConnectionError(f"Cannot connect to Vault at {self.vault_addr}: {exc}") from exc
        except (ConnectionError, OSError) as exc:
            raise VaultConnectionError(f"Cannot reach Vault at {self.vault_addr}: {exc}") from exc
        except Exception as exc:
            raise VaultError(f"Vault authentication error: {exc}") from exc

    def _refresh_token_if_needed(self) -> None:
        """Renew the Vault token if its TTL is below 5 minutes."""
        try:
            lookup = self.client.auth.token.lookup_self()
            ttl = lookup["data"]["ttl"]
            if ttl < 300:
                self._logger.info("Vault token TTL low, renewing...")
                self.client.auth.token.renew_self(increment="0")
                self._logger.info("Vault token renewed.")
        except Exception as exc:
            self._logger.warning(f"Could not refresh Vault token: {exc}")

    # ------------------------------------------------------------------
    # BaseSecretBackend interface
    # ------------------------------------------------------------------

    def add_secret(self, name: str, secret: Dict[str, Any]) -> None:
        """Store a new secret at *name*."""
        self._refresh_token_if_needed()
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=name,
                secret=secret,
                mount_point=self.mount_point,
            )
            self._logger.info(f"Secret added: {name}")
        except Exception as exc:
            raise VaultError(f"Failed to add secret '{name}': {exc}") from exc

    def get_secret(self, name: str) -> Dict[str, Any]:
        """Retrieve a secret by *name*."""
        self._refresh_token_if_needed()
        try:
            response = self.client.secrets.kv.v2.read_secret(
                path=name,
                mount_point=self.mount_point,
            )
            return response["data"]["data"]
        except Exception as exc:
            raise VaultError(f"Failed to get secret '{name}': {exc}") from exc

    def update_secret(self, name: str, secret: Dict[str, Any]) -> None:
        """Update an existing secret."""
        self._refresh_token_if_needed()
        try:
            self.client.secrets.kv.v2.patch(
                path=name,
                secret=secret,
                mount_point=self.mount_point,
            )
            self._logger.info(f"Secret updated: {name}")
        except Exception as exc:
            raise VaultError(f"Failed to update secret '{name}': {exc}") from exc

    def delete_secret(self, name: str) -> None:
        """Permanently delete a secret and all its versions."""
        self._refresh_token_if_needed()
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=name,
                mount_point=self.mount_point,
            )
            self._logger.info(f"Secret deleted: {name}")
        except Exception as exc:
            raise VaultError(f"Failed to delete secret '{name}': {exc}") from exc

    def list_secrets(self, path: str = "") -> List[str]:
        """List secret keys under *path*."""
        self._refresh_token_if_needed()
        try:
            response = self.client.secrets.kv.v2.list_secrets(
                path=path,
                mount_point=self.mount_point,
            )
            return response["data"]["keys"]
        except Exception as exc:
            raise VaultError(f"Failed to list secrets at '{path}': {exc}") from exc

    # ------------------------------------------------------------------
    # Extra helpers
    # ------------------------------------------------------------------

    def get_config(self) -> Optional[Dict[str, Any]]:
        """Return the KV engine configuration for the current mount point."""
        self._refresh_token_if_needed()
        try:
            return self.client.secrets.kv.v2.read_configuration(
                mount_point=self.mount_point
            )
        except Exception as exc:
            raise VaultError(
                f"Failed to read config for mount '{self.mount_point}': {exc}"
            ) from exc

    def read_secret_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """Return metadata and version info for *name*."""
        self._refresh_token_if_needed()
        try:
            return self.client.secrets.kv.v2.read_secret_metadata(
                path=name,
                mount_point=self.mount_point,
            )
        except Exception as exc:
            raise VaultError(f"Failed to read metadata for '{name}': {exc}") from exc

    def delete_secret_versions(self, name: str, versions: List[int]) -> None:
        """Soft-delete specific versions of *name*."""
        self._refresh_token_if_needed()
        try:
            self.client.secrets.kv.v2.delete_secret_versions(
                path=name,
                versions=versions,
                mount_point=self.mount_point,
            )
            self._logger.info(f"Soft-deleted versions {versions} of '{name}'.")
        except Exception as exc:
            raise VaultError(
                f"Failed to delete versions {versions} of '{name}': {exc}"
            ) from exc

    def undelete_secret_versions(self, name: str, versions: List[int]) -> None:
        """Restore soft-deleted versions of *name*."""
        self._refresh_token_if_needed()
        try:
            self.client.secrets.kv.v2.undelete_secret_versions(
                path=name,
                versions=versions,
                mount_point=self.mount_point,
            )
            self._logger.info(f"Undeleted versions {versions} of '{name}'.")
        except Exception as exc:
            raise VaultError(
                f"Failed to undelete versions {versions} of '{name}': {exc}"
            ) from exc

    def destroy_secret_versions(self, name: str, versions: List[int]) -> None:
        """Permanently destroy specific versions of *name*."""
        self._refresh_token_if_needed()
        try:
            self.client.secrets.kv.v2.destroy_secret_versions(
                path=name,
                versions=versions,
                mount_point=self.mount_point,
            )
            self._logger.info(f"Destroyed versions {versions} of '{name}'.")
        except Exception as exc:
            raise VaultError(
                f"Failed to destroy versions {versions} of '{name}': {exc}"
            ) from exc
