from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)
from django_email_learning.services.command_models.enroll_command import EnrollCommand
from django_email_learning.services.command_models.verify_enrollment_command import (
    VerifyEnrollmentCommand,
)
from django_email_learning.models import Course, Enrollment, EnrollmentStatus
from google_auth_oauthlib.flow import Flow  #  type: ignore
from typing import Literal
from django.conf import settings
from urllib import error, parse, request
from django.urls import reverse
import json


DJANGO_EMAIL_LEARNING_SETTINGS: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})


class EnrollFromGoogleDirectoryCommand(AbstractCommand):
    command_name: Literal[
        "enroll_from_google_directory"
    ] = "enroll_from_google_directory"
    code: str | None = None
    course_id: int
    state: str | None = None
    code_verifier: str | None = None

    def _build_flow(self) -> Flow:
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": DJANGO_EMAIL_LEARNING_SETTINGS.get(
                        "GOOGLE_OAUTH_CLIENT_ID"
                    ),
                    "client_secret": DJANGO_EMAIL_LEARNING_SETTINGS.get(
                        "GOOGLE_OAUTH_CLIENT_SECRET"
                    ),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=["https://www.googleapis.com/auth/admin.directory.user.readonly"],
            state=self.state,
        )
        flow.redirect_uri = DJANGO_EMAIL_LEARNING_SETTINGS.get(
            "SITE_BASE_URL", "http://localhost:8000"
        ) + reverse("django_email_learning:oauth_integrations:redirect_view")
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

    def execute(self) -> None:
        if not self.code or not self.state:
            raise ValueError(
                "Authorization code and state are required to enroll from Google Directory"
            )
        if not self.code_verifier:
            raise ValueError(
                "Code verifier is required to enroll from Google Directory"
            )

        course = Course.objects.get(id=self.course_id)

        flow = self._build_flow()
        flow.code_verifier = self.code_verifier

        flow.fetch_token(code=self.code)
        credentials = flow.credentials

        access_token = credentials.token
        if not access_token:
            raise ValueError("Unable to retrieve access token from Google OAuth flow")

        users_endpoint = "https://admin.googleapis.com/admin/directory/v1/users"
        page_token: str | None = None
        enrolled_count = 0
        failed_count = 0

        while True:
            query = {
                "customer": "my_customer",
                "orderBy": "email",
                "maxResults": 500,
            }
            if page_token:
                query["pageToken"] = page_token
            url = f"{users_endpoint}?{parse.urlencode(query)}"

            req = request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
                method="GET",
            )

            try:
                with request.urlopen(req) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except error.HTTPError as e:
                details = e.read().decode("utf-8") if e.fp else str(e)
                raise ValueError(
                    f"Google Directory API request failed: {details}"
                ) from e

            users = payload.get("users", [])
            for user in users:
                email = user.get("primaryEmail")
                if not email:
                    continue
                try:
                    EnrollCommand(
                        email=email,
                        course_slug=course.slug,
                        organization_id=course.organization_id,
                        no_verification=True,
                    ).execute()
                    enrolled_count += 1
                    enrollment = Enrollment.objects.get(
                        learner__email=email,
                        course_id=self.course_id,
                        status=EnrollmentStatus.UNVERIFIED,
                    )
                    VerifyEnrollmentCommand(
                        enrollment_id=enrollment.id,
                        verification_code=enrollment.activation_code,  # type: ignore[arg-type]
                    ).execute()
                except Exception as e:  # noqa: BLE001
                    failed_count += 1
                    self.logger.warning(
                        "Failed to enroll %s from Google Directory: %s", email, str(e)
                    )

            page_token = payload.get("nextPageToken")
            if not page_token:
                break

        self.logger.info(
            "Google Directory import finished for course_id=%s: enrolled=%s failed=%s",
            self.course_id,
            enrolled_count,
            failed_count,
        )
