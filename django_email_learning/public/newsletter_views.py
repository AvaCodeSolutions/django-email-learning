import uuid

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from django_email_learning.models import NewsletterSubscriber


class NewsletterUnsubscribeView(View):
    def get(self, request: HttpRequest, token: uuid.UUID) -> HttpResponse:
        try:
            subscriber = NewsletterSubscriber.objects.select_related("newsletter").get(unsubscribe_token=token)
        except NewsletterSubscriber.DoesNotExist:
            return render(
                request,
                "newsletters/unsubscribe_invalid.html",
                status=410,
            )

        newsletter_title = subscriber.newsletter.title
        subscriber.delete()
        return render(
            request,
            "newsletters/unsubscribed.html",
            {"newsletter_title": newsletter_title},
        )
