import csv
import io
import json
from django.views import View
from django.utils.decorators import method_decorator
from django.db.utils import IntegrityError
from django.http import HttpResponse, JsonResponse
from pydantic import ValidationError
from django_email_learning.platform.api import serializers
from django_email_learning.platform.api.pagniated_api_mixin import PaginatedApiMixin
from django_email_learning.models import (
    Newsletter,
    NewsletterSubscriber,
    Sendout,
)
from django_email_learning.decorators import accessible_for


@method_decorator(accessible_for(roles={"admin", "editor", "viewer"}), name="get")
@method_decorator(accessible_for(roles={"admin"}), name="post")
class NewsletterView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        newsletters = Newsletter.objects.filter(
            organization_id=kwargs["organization_id"]
        ).prefetch_related("subscribers")
        return JsonResponse(
            {
                "newsletters": [
                    serializers.NewsletterResponse.from_django_model(n).model_dump()
                    for n in newsletters
                ]
            },
            status=200,
        )

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            payload = json.loads(request.body)
            serializer = serializers.CreateNewsletterRequest.model_validate(payload)
            newsletter = serializer.to_django_model(
                organization_id=kwargs["organization_id"]
            )
            newsletter.save()
            return JsonResponse(
                serializers.NewsletterResponse.from_django_model(
                    newsletter
                ).model_dump(),
                status=201,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError:
            return JsonResponse(
                {
                    "error": "A newsletter with this title already exists for the organization."
                },
                status=409,
            )


@method_decorator(accessible_for(roles={"admin"}), name="delete")
class SingleNewsletterView(View):
    def delete(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            newsletter = Newsletter.objects.get(
                id=kwargs["newsletter_id"],
                organization_id=kwargs["organization_id"],
            )
            newsletter.delete()
            return JsonResponse({}, status=204)
        except Newsletter.DoesNotExist:
            return JsonResponse({"error": "Newsletter not found."}, status=404)


@method_decorator(accessible_for(roles={"admin", "editor", "viewer"}), name="get")
@method_decorator(accessible_for(roles={"admin"}), name="post")
class SendoutView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            newsletter = Newsletter.objects.get(
                id=kwargs["newsletter_id"],
                organization_id=kwargs["organization_id"],
            )
        except Newsletter.DoesNotExist:
            return JsonResponse({"error": "Newsletter not found."}, status=404)

        status_filter = request.GET.get("status", Sendout.Status.SCHEDULED)
        sendouts = newsletter.sendouts.all()
        if status_filter in (
            Sendout.Status.SCHEDULED,
            Sendout.Status.SENT,
        ):
            sendouts = sendouts.filter(status=status_filter)

        return JsonResponse(
            {
                "sendouts": [
                    serializers.SendoutResponse.model_validate(s).model_dump()
                    for s in sendouts.order_by("scheduled_at")
                ]
            },
            status=200,
        )

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            newsletter = Newsletter.objects.get(
                id=kwargs["newsletter_id"],
                organization_id=kwargs["organization_id"],
            )
        except Newsletter.DoesNotExist:
            return JsonResponse({"error": "Newsletter not found."}, status=404)

        try:
            payload = json.loads(request.body)
            data = serializers.CreateSendoutRequest.model_validate(payload)
            sendout = Sendout.objects.create(
                newsletter=newsletter,
                subject=data.subject,
                body=data.body,
                scheduled_at=data.scheduled_at,
            )
            return JsonResponse(
                serializers.SendoutResponse.model_validate(sendout).model_dump(),
                status=201,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)


@method_decorator(accessible_for(roles={"admin", "editor", "viewer"}), name="get")
@method_decorator(accessible_for(roles={"admin"}), name="patch")
@method_decorator(accessible_for(roles={"admin"}), name="delete")
class SingleSendoutView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            sendout = Sendout.objects.get(
                id=kwargs["sendout_id"],
                newsletter_id=kwargs["newsletter_id"],
                newsletter__organization_id=kwargs["organization_id"],
            )
        except Sendout.DoesNotExist:
            return JsonResponse({"error": "Sendout not found."}, status=404)
        return JsonResponse(
            serializers.SendoutDetailResponse.model_validate(sendout).model_dump(),
            status=200,
        )

    def patch(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            sendout = Sendout.objects.get(
                id=kwargs["sendout_id"],
                newsletter_id=kwargs["newsletter_id"],
                newsletter__organization_id=kwargs["organization_id"],
            )
        except Sendout.DoesNotExist:
            return JsonResponse({"error": "Sendout not found."}, status=404)

        if sendout.status == Sendout.Status.SENT:
            return JsonResponse(
                {"error": "Cannot edit a sendout that has already been sent."},
                status=409,
            )

        try:
            payload = json.loads(request.body)
            data = serializers.UpdateSendoutRequest.model_validate(payload)
            sendout.subject = data.subject
            sendout.body = data.body
            sendout.scheduled_at = data.scheduled_at
            sendout.save(update_fields=["subject", "body", "scheduled_at"])
            return JsonResponse(
                serializers.SendoutDetailResponse.model_validate(sendout).model_dump(),
                status=200,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)

    def delete(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            sendout = Sendout.objects.get(
                id=kwargs["sendout_id"],
                newsletter_id=kwargs["newsletter_id"],
                newsletter__organization_id=kwargs["organization_id"],
            )
        except Sendout.DoesNotExist:
            return JsonResponse({"error": "Sendout not found."}, status=404)

        if sendout.status == Sendout.Status.SENT:
            return JsonResponse(
                {"error": "Cannot delete a sendout that has already been sent."},
                status=409,
            )

        sendout.delete()
        return JsonResponse({}, status=204)


@method_decorator(accessible_for(roles={"admin", "editor", "viewer"}), name="get")
class SubscriberView(PaginatedApiMixin, View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        # Override to cap page_size at 30
        request.GET = request.GET.copy()
        page_size = min(int(request.GET.get("page_size", 30)), 30)
        request.GET["page_size"] = str(page_size)
        return super().get(request, *args, **kwargs)

    def get_query_set(self, request):  # type: ignore[no-untyped-def]
        return NewsletterSubscriber.objects.filter(
            newsletter_id=self.kwargs["newsletter_id"],
            newsletter__organization_id=self.kwargs["organization_id"],
        ).order_by("subscribed_at")

    def get_item_serializer_class(self):  # type: ignore[no-untyped-def]
        return serializers.NewsletterSubscriberResponse


@method_decorator(accessible_for(roles={"admin"}), name="delete")
class SingleSubscriberView(View):
    def delete(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            subscriber = NewsletterSubscriber.objects.get(
                id=kwargs["subscriber_id"],
                newsletter_id=kwargs["newsletter_id"],
                newsletter__organization_id=kwargs["organization_id"],
            )
        except NewsletterSubscriber.DoesNotExist:
            return JsonResponse({"error": "Subscriber not found."}, status=404)
        subscriber.delete()
        return JsonResponse({}, status=204)


@method_decorator(accessible_for(roles={"admin"}), name="get")
class SubscribersCsvExportView(View):
    def get(self, request, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        try:
            newsletter = Newsletter.objects.get(
                id=kwargs["newsletter_id"],
                organization_id=kwargs["organization_id"],
            )
        except Newsletter.DoesNotExist:
            return JsonResponse({"error": "Newsletter not found."}, status=404)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "email", "subscribed_at"])
        for sub in newsletter.subscribers.all().order_by("subscribed_at"):
            writer.writerow([sub.id, sub.email, sub.subscribed_at.isoformat()])

        response = HttpResponse(output.getvalue(), content_type="text/csv")
        safe_title = newsletter.title.replace('"', "")
        response[
            "Content-Disposition"
        ] = f'attachment; filename="{safe_title}_subscribers.csv"'
        return response
