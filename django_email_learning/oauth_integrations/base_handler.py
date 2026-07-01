from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class BaseOAuthSessionHandler(ABC, BaseModel):
    provider_and_purpose: str
    state: str | None = None
    code: str | None = None

    def access_allowed(self, request: Any) -> bool:
        """Hook for library users to gate access to this OAuth session handler.

        Override in a subclass to implement custom access logic (e.g. feature
        flags, subscription plans). Runs before the standard role-based
        access checks in SessionsView.
        """
        return True

    @abstractmethod
    def handle_redirect(self) -> str:
        """
        Handles the OAuth redirect and returns the access_token
        """
        raise NotImplementedError("Subclasses must implement the handle_redirect method")

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """
        Returns the authorization URL to redirect the user to for OAuth authentication
        """
        raise NotImplementedError("Subclasses must implement the get_authorization_url method")
