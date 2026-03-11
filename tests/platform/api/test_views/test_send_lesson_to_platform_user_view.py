import json
from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from django_email_learning.platform.api.views import SendLessonToPlatformUser


@pytest.mark.parametrize("user_key", ["editor_user", "organization_admin"])
@patch("django_email_learning.platform.api.views.SendLessonCommand")
def test_send_lesson_to_platform_user_sends_email_for_allowed_roles(
    mock_send_lesson_command,
    db,
    users,
    course_lesson_content,
    user_key,
):
    request = RequestFactory().post(
        "/api/platform/organizations/1/lessons/send/",
        data=json.dumps({"id": course_lesson_content.id}),
        content_type="application/json",
    )
    request.user = users[user_key]

    response = SendLessonToPlatformUser.as_view()(request, organization_id=1)

    assert response.status_code == 200
    mock_send_lesson_command.assert_called_once_with(
        content_id=course_lesson_content.id,
        email=users[user_key].email,
    )
    mock_send_lesson_command.return_value.execute.assert_called_once_with()


@patch("django_email_learning.platform.api.views.SendLessonCommand")
def test_send_lesson_to_platform_user_forbidden_for_viewer(
    mock_send_lesson_command,
    db,
    users,
    course_lesson_content,
):
    request = RequestFactory().post(
        "/api/platform/organizations/1/lessons/send/",
        data=json.dumps({"id": course_lesson_content.id}),
        content_type="application/json",
    )
    request.user = users["viewer_user"]

    response = SendLessonToPlatformUser.as_view()(request, organization_id=1)

    assert response.status_code == 403
    mock_send_lesson_command.assert_not_called()


@patch("django_email_learning.platform.api.views.SendLessonCommand")
def test_send_lesson_to_platform_user_unauthorized_for_anonymous(
    mock_send_lesson_command,
    db,
    course_lesson_content,
):
    request = RequestFactory().post(
        "/api/platform/organizations/1/lessons/send/",
        data=json.dumps({"id": course_lesson_content.id}),
        content_type="application/json",
    )
    request.user = AnonymousUser()

    response = SendLessonToPlatformUser.as_view()(request, organization_id=1)

    assert response.status_code == 401
    mock_send_lesson_command.assert_not_called()
