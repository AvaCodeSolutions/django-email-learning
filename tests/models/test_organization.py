from django_email_learning.models import Learner, Organization


def test_get_learners_cap_defaults_to_unlimited(db, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "LEARNERS": {}}
    organization = Organization.objects.get(id=1)
    assert organization.get_learners_cap() == 0


def test_get_learners_cap_reads_settings(db, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "LEARNERS": {"MAX_LEARNERS_PER_ORGANIZATION": 3},
    }
    organization = Organization.objects.get(id=1)
    assert organization.get_learners_cap() == 3


def test_can_enroll_learner_unlimited_by_default(db):
    organization = Organization.objects.get(id=1)
    assert organization.can_enroll_learner() is True


def test_can_enroll_learner_false_when_cap_reached(db, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "LEARNERS": {"MAX_LEARNERS_PER_ORGANIZATION": 1},
    }
    organization = Organization.objects.get(id=1)
    Learner.objects.create(email="learner@example.com", organization=organization)
    assert organization.can_enroll_learner() is False


def test_can_enroll_learner_true_when_under_cap(db, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "LEARNERS": {"MAX_LEARNERS_PER_ORGANIZATION": 2},
    }
    organization = Organization.objects.get(id=1)
    Learner.objects.create(email="learner@example.com", organization=organization)
    assert organization.can_enroll_learner() is True
