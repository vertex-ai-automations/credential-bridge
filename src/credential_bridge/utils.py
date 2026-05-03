import json
import logging
import os
import warnings
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests

CONFIG_FILE: Path = Path.home() / ".vault_config.json"

logger = logging.getLogger(__name__)


def local_path(relative_path: str) -> str:
    """Return absolute path to a file relative to this module."""
    return str(Path(__file__).parent / relative_path)


def load_welcome_banner(file_path: str) -> str:
    """Load and return the contents of a welcome banner file."""
    with open(local_path(file_path), "r", encoding="utf-8") as f:
        return f.read()


def save_config(data: Dict[str, Any]) -> None:
    """Save configuration data to CONFIG_FILE as JSON."""
    import sys
    if sys.platform != "win32":
        # Write with restricted permissions so only the owner can read the file
        fd = os.open(str(CONFIG_FILE), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    else:
        # Windows: NTFS ACLs require win32security; write normally and warn the user
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        warnings.warn(
            f"Vault config written to {CONFIG_FILE} without restricted permissions. "
            "Consider restricting file access manually on Windows.",
            UserWarning,
            stacklevel=2,
        )


def load_config() -> Dict[str, Any]:
    """Load configuration data from CONFIG_FILE. Returns empty dict if file doesn't exist."""
    logger.debug("Loading config file...")
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_vault_credentials() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Retrieve vault credentials from config.

    Returns:
        Tuple of (vault_token, vault_role_id, vault_secret_id)
    """
    logger.debug("Getting vault credentials...")
    config = load_config()
    return (
        config.get("vault_token"),
        config.get("vault_role_id"),
        config.get("vault_secret_id"),
    )


def get_session(
    cert: Optional[str] = None,
    proxies: Optional[Dict[str, str]] = None,
) -> requests.Session:
    """
    Create and configure a requests Session.

    Args:
        cert: Optional path to a certificate file for verification
        proxies: Optional dict of proxy settings

    Returns:
        Configured requests.Session instance
    """
    session = requests.Session()
    session.trust_env = False
    session.verify = cert if cert else True
    session.proxies = proxies or {}
    if cert:
        logger.debug("Session created with custom cert: %s", cert)
    if proxies:
        logger.debug("Session created with proxies configured (%d entries)", len(proxies))
    return session


