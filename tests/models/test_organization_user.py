from django.core.exceptions import ValidationError

from django_email_learning.models.organizations import OrganizationUser
import pytest


def test_instructor_organization_user_requires_display_name(db, users):
    with pytest.raises(ValidationError) as exc_info:
        OrganizationUser.objects.create(
            user=users["instructor_user"],
            organization_id=1,
            role="instructor",
        )
    assert "Instructor role requires a display name." in str(exc_info.value)
