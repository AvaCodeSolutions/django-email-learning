from django_email_learning.platform.views.base import BasePlatformView
from django_email_learning.platform.views.courses import Courses, CourseView
from django_email_learning.platform.views.organisations import (
    Organizations,
    SingleOrganization,
)
from django_email_learning.platform.views.newsletters import (
    NewsletterDetailView,
    NewsletterSubscribersView,
)
from django_email_learning.platform.views.learners import Learners
from django_email_learning.platform.views.misc import (
    ApiKeys,
    PrivateFileView,
    Analytics,
)

__all__ = [
    "BasePlatformView",
    "Courses",
    "CourseView",
    "Organizations",
    "SingleOrganization",
    "NewsletterDetailView",
    "NewsletterSubscribersView",
    "Learners",
    "ApiKeys",
    "PrivateFileView",
    "Analytics",
]
