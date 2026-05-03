"""Abstract base class for all secret backends."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseSecretBackend(ABC):
    """Contract that every secrets backend must fulfil."""

    backend_name: str = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # __abstractmethods__ is not yet populated when __init_subclass__ runs,
        # so we collect abstract method names from the MRO manually.
        abstract_names = {
            name
            for base in cls.__mro__
            for name, val in vars(base).items()
            if getattr(val, "__isabstractmethod__", False)
        }
        # Only enforce backend_name on concrete (fully-implemented) subclasses
        overridden = {
            name
            for name in abstract_names
            if name in cls.__dict__ and not getattr(cls.__dict__[name], "__isabstractmethod__", False)
        }
        if abstract_names and overridden >= abstract_names:
            # All abstract methods are implemented — this is a concrete subclass
            if not cls.backend_name:
                raise TypeError(
                    f"{cls.__name__} must define a non-empty 'backend_name' class attribute."
                )

    @abstractmethod
    def add_secret(self, name: str, secret: Dict[str, Any]) -> None:
        """Store a new secret. Creates a new version if the secret already exists (Vault); raises if key already exists (EnvFile)."""

    @abstractmethod
    def get_secret(self, name: str) -> Dict[str, Any]:
        """Retrieve a secret by name. Raises if not found."""

    @abstractmethod
    def update_secret(self, name: str, secret: Dict[str, Any]) -> None:
        """Update an existing secret. Raises if not found."""

    @abstractmethod
    def delete_secret(self, name: str) -> None:
        """Delete a secret. Raises if not found."""

    @abstractmethod
    def list_secrets(self, path: str = "") -> List[str]:
        """List secret names, optionally under a path prefix."""
