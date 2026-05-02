import os
from typing import Dict, List, Optional, Union

import hvac
import urllib3
from pylogshield import PyLogShield, LogLevel, get_logger

from .utils import VaultManagerError, get_session, load_config, save_config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class VaultManager:
    """Class for managing credentials using HashiCorp Vault."""

    def __init__(
        self,
        vault_addr: Optional[str] = None,
        vault_token: Optional[str] = None,
        vault_role_id: Optional[str] = None,
        vault_secret_id: Optional[str] = None,
        service_name: str = "default_service",
        proxies: Optional[Dict[str, str]] = None,
        cert: Optional[str] = None,
        log_level: Union[LogLevel, str] = LogLevel.WARNING,
        logger: PyLogShield = None,
        mask: bool = True,
        mount_point: Optional[str] = None,
    ):
        self.mask = mask
        self.service_name = service_name

        # It must use PylogShield because it supports sensitive masking
        if logger and not isinstance(logger, PyLogShield):
            raise VaultManagerError(
                "logger must be instance of PyLogShield. Please use 'from pylogshield import PyLogShield'"
            )

        self.logger = logger or get_logger(name="credential_bridge", log_level=log_level)
        self.username = os.getenv("USERNAME", "default_user").upper()
        self.mount_point = mount_point or f"{self.username}"  # /data
        self.cert = cert if cert else False
        self.proxies = proxies
        self.session = get_session(cert, proxies)

        config = load_config()

        # Get vault_addr from parameter, environment variable, or config
        if vault_addr:
            self.vault_addr = vault_addr
        else:
            self.vault_addr = os.getenv("VAULT_ADDR") or config.get("vault_addr")

        if not self.vault_addr:
            raise VaultManagerError("Vault address must be provided via vault_addr parameter, VAULT_ADDR environment variable, or ~/.vault_config.json")

        # If user did not provide creds then get from config file
        self.vault_token = vault_token if vault_token else config.get("vault_token")
        self.vault_role_id = vault_role_id if vault_role_id else config.get("vault_role_id")
        self.vault_secret_id = vault_secret_id if vault_secret_id else config.get("vault_secret_id")

        # Raise error if both creds types are provided
        if self.vault_token and (self.vault_role_id or self.vault_secret_id):
            raise VaultManagerError("Provide either a Vault token or Approle credentials, not both.")

        # Raise error if no credentials are provided
        if not self.vault_token and not (self.vault_role_id and self.vault_secret_id):
            raise VaultManagerError(
                "No authentication method provided. Please provide either a token or AppRole credentials."
            )

        # Update the config with provided credentials
        if vault_token:
            config["vault_token"] = vault_token
            config["vault_role_id"] = None
            config["vault_secret_id"] = None
        elif vault_role_id and vault_secret_id:
            config["vault_role_id"] = vault_role_id
            config["vault_secret_id"] = vault_secret_id
            config["vault_token"] = None

        save_config(config)

        self.client = self._authenticate()

    def get_vault_creds(self):
        return self.vault_token, self.vault_role_id, self.vault_secret_id

    def _authenticate(self):
        """Authenticate with Vault using token or AppRole."""
        self.logger.info("Authenticating with Vault...")
        try:
            if self.vault_token:
                client = hvac.Client(
                    url=self.vault_addr,
                    token=self.vault_token,
                    session=self.session,
                    proxies=self.proxies,
                    verify=self.cert,
                )
                if client.is_authenticated():
                    self.logger.info("Successfully authenticated with Vault using token.")
                    return client
                else:
                    raise VaultManagerError("Failed to authenticate with Vault using token.")
            elif self.vault_role_id and self.vault_secret_id:
                client = hvac.Client(url=self.vault_addr, session=self.session, proxies=self.proxies, verify=self.cert)
                auth_response = client.auth.approle.login(role_id=self.vault_role_id, secret_id=self.vault_secret_id)
                if "auth" in auth_response and "client_token" in auth_response["auth"]:
                    token = auth_response["auth"]["client_token"]
                    client.token = token
                    self.logger.info("Successfully authenticated with Vault using AppRole.")
                    return client
                else:
                    raise VaultManagerError("Failed to authenticate with Vault using AppRole.")
            else:
                raise VaultManagerError(
                    "No authentication method provided. Please provide either a token or AppRole credentials."
                )
        except Exception as e:
            self.logger.error(f"Failed to connect with Vault: {e}")
            raise VaultManagerError(f"Failed to connect with Vault: {e}")

    def _refresh_token_if_needed(self):
        """Refresh the Vault token if needed."""
        try:
            self.logger.info("Checking Vault token status...")
            lookup_response = self.client.auth.token.lookup_self()
            ttl = lookup_response["data"]["ttl"]

            if ttl < 300:  # If token's TTL is less than 5 minutes
                self.logger.info("Vault token is about to expire, refreshing...")
                self.client.auth.token.renew_self(increment="0")
                self.logger.info("Successfully refreshed Vault token.")
            else:
                self.logger.info("Vault token is still valid.")
        except Exception as e:
            self.logger.error(f"Failed to refresh Vault token: {e}")

    def add_secret(self, name: str, secret: Dict[str, str]) -> None:
        """Add secrets to vault."""
        self._refresh_token_if_needed()
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=name,
                secret=secret,
                mount_point=self.mount_point,
            )
            self.logger.info(f"Credentials successfully added: \nName: {name}")
            self.logger.info(secret, mask=self.mask)
        except Exception as e:
            self.logger.error(f"Failed to add secret for {name}: {e}")

    def get_secret(self, name: str) -> Optional[Dict[str, str]]:
        """Get secrets from vault"""
        self._refresh_token_if_needed()
        try:
            secret_response = self.client.secrets.kv.v2.read_secret(path=name, mount_point=self.mount_point)
            secret = secret_response["data"]["data"]
            self.logger.info(f"Credentials successfully retrieved: \nName: {name}")
            self.logger.info(secret, mask=self.mask)
            return secret
        except Exception as e:
            self.logger.error(f"Failed to retrieve secret for {name}: {e}")
            return None

    def get_config(self) -> Optional[Dict[str, str]]:
        """Get vault configurations."""
        self._refresh_token_if_needed()
        try:
            secret_response = self.client.secrets.kv.v2.read_configuration(mount_point=self.mount_point)
            self.logger.info(f"Configuration retrieved: \nMount: {self.mount_point}")
            return secret_response
        except Exception as e:
            self.logger.error(f"Failed to retrieve configuration for {self.mount_point}: {e}")
            return None

    def delete_secret(self, name: str) -> None:
        """Delete secrets from vault"""
        self._refresh_token_if_needed()
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(path=name, mount_point=self.mount_point)
            self.logger.info(
                f"Credentials successfully deleted (permanently) the key metadata and all version data for: \nName: {name}"
            )
        except Exception as e:
            self.logger.error(f"Failed to delete secret for {name}: {e}")

    def update_secret(self, name: str, secret: Dict[str, str]) -> None:
        """Update secrets in vault"""
        self._refresh_token_if_needed()
        try:
            self.client.secrets.kv.v2.patch(path=name, secret=secret, mount_point=self.mount_point)
            self.logger.info(f"Credentials successfully updated: \nName: {name}")
            self.logger.info(secret, mask=self.mask)
        except Exception as e:
            self.logger.error(f"Failed to update secret for {name}: {e}")

    def list_secrets(self, name: str) -> List[str]:
        """Retrieve list of secrest from vault"""
        self._refresh_token_if_needed()
        try:
            secrets_list = self.client.secrets.kv.v2.list_secrets(path=name, mount_point=self.mount_point)
            self.logger.info(f"Secrets listed in {name}.")
            return secrets_list  # ['data']['keys']
        except Exception as e:
            self.logger.error(f"Failed to list secrets in {name}: {e}")
            return []

    def read_secret_metadata(self, name: str) -> Optional[Dict[str, str]]:
        """Retrieve secrets metadata."""
        self._refresh_token_if_needed()
        try:
            secret_metadata = self.client.secrets.kv.v2.read_secret_metadata(path=name, mount_point=self.mount_point)
            self.logger.info(f"Retrieve the metadata and versions for {name} from Vault.")
            return secret_metadata  # ['data']
        except Exception as e:
            self.logger.error(f"Failed to retrieve secret metadata for {name}: {e}")
            return None

    def delete_secret_versions(self, name: str, versions: List[int]) -> None:
        """Delete stored secrets version."""
        self._refresh_token_if_needed()
        try:
            self.client.secrets.kv.v2.delete_secret_versions(path=name, versions=versions, mount_point=self.mount_point)
            self.logger.info(
                f"Credentials versions successfully deleted (soft delete): \nVersions: {versions}\nSecret: {name}",
                mask=self.mask,
            )
        except Exception as e:
            self.logger.error(f"Failed to delete versions {versions} of secret {name}: {e}")

    def undelete_secret_versions(self, name: str, versions: List[int]) -> None:
        """Restore deleted secret version."""
        self._refresh_token_if_needed()
        try:
            self.client.secrets.kv.v2.undelete_secret_versions(
                path=name, versions=versions, mount_point=self.mount_point
            )
            self.logger.info(
                f"Credentials versions successfully undeleted: \nVersions: {versions}\nSecret: {name}", mask=self.mask
            )
        except Exception as e:
            self.logger.error(f"Failed to undelete versions {versions} of secret {name}: {e}")

    def destroy_secret_versions(self, name: str, versions: List[int]) -> None:
        """Permanently destroy secrets."""
        self._refresh_token_if_needed()
        try:
            self.client.secrets.kv.v2.destroy_secret_versions(
                path=name, versions=versions, mount_point=self.mount_point
            )
            self.logger.info(
                f"Permanently remove the specified version data and numbers: \nVersions: {versions}\nSecret: {name}",
                mask=self.mask,
            )
        except Exception as e:
            self.logger.error(f"Failed to destroy versions {versions} of secret {name}: {e}")
