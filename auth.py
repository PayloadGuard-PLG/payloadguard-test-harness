# PayloadGuard smoke test
"""
Authentication module.
Handles user login, logout, session management, and password validation.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional


class SessionManager:
    """Manages active user sessions."""

    def __init__(self):
        self._sessions: dict[str, dict] = {}

    def create(self, user_id: str, ttl_minutes: int = 60) -> str:
        token = secrets.token_hex(32)
        self._sessions[token] = {
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=ttl_minutes),
        }
        return token

    def validate(self, token: str) -> Optional[str]:
        session = self._sessions.get(token)
        if not session:
            return None
        if datetime.utcnow() > session["expires_at"]:
            self.revoke(token)
            return None
        return session["user_id"]

    def revoke(self, token: str) -> bool:
        return self._sessions.pop(token, None) is not None

    def revoke_all(self, user_id: str) -> int:
        to_revoke = [t for t, s in self._sessions.items() if s["user_id"] == user_id]
        for token in to_revoke:
            del self._sessions[token]
        return len(to_revoke)


class PasswordValidator:
    """Validates and hashes passwords."""

    MIN_LENGTH = 8

    def validate_strength(self, password: str) -> tuple[bool, str]:
        if len(password) < self.MIN_LENGTH:
            return False, f"Password must be at least {self.MIN_LENGTH} characters"
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"
        return True, "OK"

    def hash(self, password: str, salt: Optional[str] = None) -> tuple[str, str]:
        salt = salt or secrets.token_hex(16)
        hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return hashed, salt

    def verify(self, password: str, hashed: str, salt: str) -> bool:
        candidate, _ = self.hash(password, salt)
        return candidate == hashed


class Auth:
    """
    Core authentication handler.
    Coordinates login, logout, and session lifecycle.
    """

    def __init__(self):
        self._users: dict[str, dict] = {}
        self.sessions = SessionManager()
        self.validator = PasswordValidator()

    def register(self, username: str, password: str) -> bool:
        if username in self._users:
            return False
        valid, _ = self.validator.validate_strength(password)
        if not valid:
            return False
        hashed, salt = self.validator.hash(password)
        self._users[username] = {"hashed": hashed, "salt": salt, "active": True}
        return True

    def login(self, username: str, password: str) -> Optional[str]:
        user = self._users.get(username)
        if not user or not user["active"]:
            return None
        if not self.validator.verify(password, user["hashed"], user["salt"]):
            return None
        return self.sessions.create(username)

    def logout(self, token: str) -> bool:
        return self.sessions.revoke(token)

    def logout_all(self, username: str) -> int:
        return self.sessions.revoke_all(username)

    def authenticate(self, token: str) -> Optional[str]:
        return self.sessions.validate(token)

    def deactivate(self, username: str) -> bool:
        if username not in self._users:
            return False
        self._users[username]["active"] = False
        self.sessions.revoke_all(username)
        return True

    def health_check(self) -> dict:
        active = sum(
            1 for s in self.sessions._sessions.values()
            if datetime.utcnow() <= s["expires_at"]
        )
        return {
            "status": "ok",
            "registered_users": len(self._users),
            "active_sessions": active,
        }
