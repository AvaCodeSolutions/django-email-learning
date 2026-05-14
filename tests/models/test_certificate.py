from django_email_learning.models import Certificate


def test_random_suffix_is_added_on_save(enrollment):
    cert = Certificate.objects.create(
        enrollment=enrollment, name_on_certificate="John Doe"
    )

    assert cert.random_suffix is not None


def test_certificate_number(enrollment):
    cert = Certificate.objects.create(
        enrollment=enrollment, name_on_certificate="John Doe"
    )

    expected_number = f"{enrollment.course.organization.id}-{enrollment.course.id}-{cert.id}-{cert.random_suffix}"
    assert cert.certificate_number == expected_number
