from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def create_platform_admin_group(sender, **kwargs) -> None:  # type: ignore[no-untyped-def]
    if sender.name != "django_email_learning":
        return

    organization_ct = ContentType.objects.get(
        app_label="django_email_learning", model="organization"
    )
    organization_user_ct = ContentType.objects.get(
        app_label="django_email_learning", model="organizationuser"
    )
    course_ct = ContentType.objects.get(
        app_label="django_email_learning", model="course"
    )
    imap_connection_ct = ContentType.objects.get(
        app_label="django_email_learning", model="imapconnection"
    )
    lesson_ct = ContentType.objects.get(
        app_label="django_email_learning", model="lesson"
    )
    quiz_ct = ContentType.objects.get(app_label="django_email_learning", model="quiz")
    question_ct = ContentType.objects.get(
        app_label="django_email_learning", model="question"
    )
    answer_ct = ContentType.objects.get(
        app_label="django_email_learning", model="answer"
    )
    course_content_ct = ContentType.objects.get(
        app_label="django_email_learning", model="coursecontent"
    )

    perms = Permission.objects.filter(
        content_type__in=[
            organization_ct,
            organization_user_ct,
            course_ct,
            imap_connection_ct,
            lesson_ct,
            quiz_ct,
            question_ct,
            answer_ct,
            course_content_ct,
        ],
        codename__in=[
            "add_organization",
            "change_organization",
            "delete_organization",
            "add_organizationuser",
            "change_organizationuser",
            "delete_organizationuser",
            "add_course",
            "change_course",
            "delete_course",
            "add_imapconnection",
            "change_imapconnection",
            "delete_imapconnection",
            "add_lesson",
            "change_lesson",
            "delete_lesson",
            "add_quiz",
            "change_quiz",
            "delete_quiz",
            "add_question",
            "change_question",
            "delete_question",
            "add_answer",
            "change_answer",
            "delete_answer",
            "add_coursecontent",
            "change_coursecontent",
            "delete_coursecontent",
        ],
    )

    platform_admin_group, created = Group.objects.get_or_create(
        name="Email Learning Platform Admins"
    )
    platform_admin_group.permissions.set(perms)
    print("Platform Admin group created.")


@receiver(post_migrate)
def create_default_organization(sender, **kwargs):  # type: ignore[no-untyped-def]
    if sender.name != "django_email_learning":
        return

    Organization = sender.get_model("Organization")
    if not Organization.objects.count():
        organization = Organization.objects.create(name="My Organization")
        organization.save()
        print("Default organization 'My Organization' created.")
