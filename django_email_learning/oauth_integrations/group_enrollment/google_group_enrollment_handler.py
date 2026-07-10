import base64
import logging
import os
from typing import TYPE_CHECKING

from django.conf import settings

from django_email_learning.oauth_integrations.models import Session
from django_email_learning.services.jwt_service import decode_jwt

from .base_group_enrollment_handler import BaseGroupEnrollmentHandler, Group, User

if TYPE_CHECKING:
    from google_auth_oauthlib.flow import Flow  # type: ignore
import json
from typing import Literal
from urllib import error, parse, request as urlrequest

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)

DJANGO_EMAIL_LEARNING_SETTINGS: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})


class GoogleGroupEnrollmentHandler(BaseGroupEnrollmentHandler):
    provider_and_purpose: Literal["google_group_enrollment"] = "google_group_enrollment"
    code_verifier: str | None = None

    def _build_flow(self) -> "Flow":
        try:
            from google_auth_oauthlib.flow import Flow  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "Google Workspace group enrollment requires the 'google' extra. "
                "Install it with: pip install django-email-learning[google]"
            ) from exc

        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": DJANGO_EMAIL_LEARNING_SETTINGS.get("GOOGLE_OAUTH", {}).get("CLIENT_ID"),
                    "client_secret": DJANGO_EMAIL_LEARNING_SETTINGS.get("GOOGLE_OAUTH", {}).get("CLIENT_SECRET"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=[
                "https://www.googleapis.com/auth/admin.directory.user.readonly",
                "https://www.googleapis.com/auth/admin.directory.group.readonly",
            ],
            state=self.state,
        )
        flow.redirect_uri = DJANGO_EMAIL_LEARNING_SETTINGS.get("SITE_BASE_URL", "http://localhost:8000") + reverse(
            "django_email_learning:oauth_integrations:redirect_view"
        )
        return flow

    def get_authorization_url(self, state: str) -> str:
        self.state = state
        flow = self._build_flow()
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            code_challenge_method="S256",
        )
        self.code_verifier = flow.code_verifier
        return authorization_url

    def handle_redirect(self) -> str:
        if not self.code or not self.state:
            raise ValueError("Authorization code and state are required to enroll from Google Directory")
        if not self.code_verifier:
            raise ValueError("Code verifier is required to enroll from Google Directory")

        flow = self._build_flow()
        flow.code_verifier = self.code_verifier

        # Google commonly grants additional scopes we didn't request (e.g.
        # openid, userinfo.email, userinfo.profile) alongside the ones we
        # did. oauthlib treats any scope mismatch as fatal by default; relax
        # that so it doesn't reject an otherwise-successful authorization.
        os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")
        flow.fetch_token(code=self.code)
        credentials = flow.credentials

        access_token = credentials.token

        if not access_token:
            raise ValueError("Unable to retrieve access token from Google OAuth flow")

        return access_token

    def get_groups(self) -> list[Group] | None:
        session = Session.objects.filter(session_id=self.state).first()
        if not session:
            raise ValueError("Session not found for state: {}".format(self.state))
        if not session.access_token:
            raise ValueError("Access token not found in session for state: {}".format(self.state))

        access_token = decode_jwt(session.access_token)["access_token"]
        url = "https://www.googleapis.com/admin/directory/v1/groups?customer=my_customer"
        req = urlrequest.Request(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            method="GET",
        )

        try:
            with urlrequest.urlopen(req) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as e:
            raise ValueError(f"Google Directory API request failed: {e}") from e

        groups = payload.get("groups", [])
        return [Group(id=group["id"], name=group["name"]) for group in groups]

    def get_users_to_enroll(self, groups: set[str] | None) -> set[User]:
        user_ids: set[str] = set()
        users: set[User] = set()
        session_id = self.state
        session = Session.objects.filter(session_id=session_id).first()
        if not session:
            raise ValueError(f"Session not found for state: {session_id}")

        if not session.access_token:
            raise ValueError(f"Access token not found in session for state: {session_id}")

        access_token = decode_jwt(session.access_token)["access_token"]

        if (groups is not None and "all" in groups) or groups is None:
            user_ids.update(self._get_user_id_for_all(access_token))
        else:
            user_ids.update(self._get_user_id_for_groups(access_token, groups))

        for user_id in user_ids:
            user = self._get_user(user_id)
            if user:
                users.add(user)

        return users

    def _get_user_id_for_groups(self, access_token: str, groups: set[str]) -> set[str]:
        user_ids = set()
        for group_id in groups:
            page_token: str | None = None
            url = f"https://www.googleapis.com/admin/directory/v1/groups/{group_id}/members"
            while True:
                query = {
                    "maxResults": "500",
                }
                if page_token:
                    query["pageToken"] = page_token

                url_with_query = f"{url}?{parse.urlencode(query)}"
                req = urlrequest.Request(
                    url_with_query,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                    method="GET",
                )

                try:
                    with urlrequest.urlopen(req) as response:
                        payload = json.loads(response.read().decode("utf-8"))
                except error.HTTPError as e:
                    raise ValueError(f"Google Directory API request failed {e.code}: {e.reason}")

                members = payload.get("members", [])
                for member in members:
                    if member.get("type") == "USER" and member.get("status") == "ACTIVE":
                        user_ids.add(member["id"])
                page_token = payload.get("nextPageToken")
                if not page_token:
                    break

        return user_ids

    def _get_user_id_for_all(self, access_token: str) -> set[str]:
        user_ids = set()
        page_token: str | None = None
        users_endpoint = "https://admin.googleapis.com/admin/directory/v1/users"
        while True:
            query = {
                "customer": "my_customer",
                "orderBy": "email",
                "maxResults": 500,
            }
            if page_token:
                query["pageToken"] = page_token
            url = f"{users_endpoint}?{parse.urlencode(query)}"

            req = urlrequest.Request(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
                method="GET",
            )

            try:
                with urlrequest.urlopen(req) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except error.HTTPError as e:
                raise ValueError(f"Google Directory API request failed: {e}") from e

            users = payload.get("users", [])
            for user in users:
                email = user.get("primaryEmail")
                is_archived = user.get("archived", False)
                is_suspended = user.get("suspended", False)
                if not email or is_archived or is_suspended:
                    continue
                user_ids.add(user.get("id"))

            page_token = payload.get("nextPageToken")
            if not page_token:
                break

        return user_ids

    def _get_user(self, user_id: str) -> User | None:
        user_endpoint = f"https://admin.googleapis.com/admin/directory/v1/users/{user_id}"
        session = Session.objects.get(session_id=self.state)
        if not session:
            raise ValueError(f"Session not found for state: {self.state}")
        if not session.access_token:
            raise ValueError(f"Access token not found in session for state: {self.state}")
        req = urlrequest.Request(
            user_endpoint,
            headers={
                "Authorization": f"Bearer {decode_jwt(session.access_token)['access_token']}",
                "Accept": "application/json",
            },
            method="GET",
        )
        with urlrequest.urlopen(req) as response:
            payload = json.loads(response.read().decode("utf-8"))

        email = payload.get("primaryEmail")

        if not email:
            return None

        photo_endpoint = f"https://www.googleapis.com/admin/directory/v1/users/{user_id}/photos/thumbnail"
        photo_req = urlrequest.Request(
            photo_endpoint,
            headers={
                "Authorization": f"Bearer {decode_jwt(session.access_token)['access_token']}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urlrequest.urlopen(photo_req) as response:
                photo_payload = json.loads(response.read().decode("utf-8"))
                data = photo_payload.get("photoData")
                mime_type = photo_payload.get("mimeType")
                file_name = f"{user_id}_photo.{mime_type.lower().replace('image/', '')}"

                if data and mime_type:
                    date_prefix = timezone.now().strftime("%Y%m%d")
                    padded_data = data + "=" * (-len(data) % 4)
                    decoded_photo = base64.urlsafe_b64decode(padded_data)

                    file_path = default_storage.save(
                        f"uploads/{date_prefix}/{self.course_id}/{file_name}",
                        ContentFile(decoded_photo),
                    )
                    logger.debug(file_path)
                    return User(email=email, photo_path=file_path)
        except error.HTTPError:
            logging.warning(f"Failed to retrieve photo for user {email} with id {user_id}")

        return User(email=email, photo_path=None)
