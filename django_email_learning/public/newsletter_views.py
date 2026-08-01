import uuid

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from django_email_learning.models import NewsletterSubscriber


@method_decorator(csrf_exempt, name="dispatch")
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

        return render(
            request,
            "newsletters/unsubscribe_confirm.html",
            {"newsletter_title": subscriber.newsletter.title},
        )

    def post(self, request: HttpRequest, token: uuid.UUID) -> HttpResponse:
        try:
            subscriber = NewsletterSubscriber.objects.select_related("newsletter").get(unsubscribe_token=token)
        except NewsletterSubscriber.DoesNotExist:
            return render(
                request,
                "newsletters/unsubscribe_invalid.html",
            )

        newsletter_title = subscriber.newsletter.title
        subscriber.delete()
        return render(
            request,
            "newsletters/unsubscribed.html",
            {"newsletter_title": newsletter_title},
        )


class NewsletterConfirmSubscriptionView(View):
    def get(self, request: HttpRequest, token: uuid.UUID) -> HttpResponse:
        try:
            subscriber = NewsletterSubscriber.objects.select_related("newsletter").get(confirm_token=token)
        except NewsletterSubscriber.DoesNotExist:
            return render(
                request,
                "newsletters/confirm_invalid.html",
                status=410,
            )

        if not subscriber.is_confirmed:
            subscriber.confirmed_at = timezone.now()
            subscriber.save(update_fields=["confirmed_at"])

        return render(
            request,
            "newsletters/subscription_confirmed.html",
            {"newsletter_title": subscriber.newsletter.title},
        )
