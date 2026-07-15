from django_email_learning.jobs.check_imap_job import CheckIMAPJob
from django_email_learning.jobs.deactivate_inactive_enrollments_job import (
    DeactivateInactiveEnrollmentsJob,
)
from django_email_learning.jobs.deliver_contents_job import DeliverContentsJob
from django_email_learning.jobs.send_newsletters_job import SendNewslettersJob
from django_email_learning.jobs.send_reminders_job import SendRemindersJob
from django_email_learning.models import JobName

JOB_REGISTRY: dict[str, type] = {
    JobName.DELIVER_CONTENTS.value: DeliverContentsJob,
    JobName.CHECK_IMAP.value: CheckIMAPJob,
    JobName.SEND_REMINDERS.value: SendRemindersJob,
    JobName.DEACTIVATE_ENROLLMENTS.value: DeactivateInactiveEnrollmentsJob,
    JobName.SEND_NEWSLETTERS.value: SendNewslettersJob,
}
