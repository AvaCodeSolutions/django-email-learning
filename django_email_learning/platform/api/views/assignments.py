import json
import logging

from django.db.utils import IntegrityError
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from pydantic import ValidationError

from django_email_learning.decorators import accessible_for
from django_email_learning.models import (
    AssignmentFeedback,
    AssignmentSubmission,
    OrganizationUser,
)
from django_email_learning.platform.api import serializers
from django_email_learning.services.command_models.send_assignment_review_command import (
    SendAssignmentReviewCommand,
)

logger = logging.getLogger(__name__)


@method_decorator(accessible_for(roles={"admin", "instructor"}), name="get")
class SubmittedAssignmentsView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        submissions = (
            AssignmentSubmission.objects.filter(
                delivery__course_content__course_id=kwargs["course_id"],
                delivery__course_content__course__organization_id=kwargs["organization_id"],
            )
            .select_related("delivery__course_content__assignment", "delivery__enrollment__learner")
            .order_by("-submitted_at")
        )
        if "status" in request.GET:
            status = request.GET["status"]
            if status in AssignmentSubmission.SubmissionStatus.values:
                submissions = submissions.filter(status=status)
        if "learner_id" in request.GET:
            submissions = submissions.filter(delivery__enrollment__learner_id=request.GET["learner_id"])
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 50))
        offset = (page - 1) * page_size
        count = submissions.count()
        response_list = []
        for submission in submissions[offset : offset + page_size]:
            response_list.append(
                serializers.AssignmentSubmissionSummaryResponse.from_django_model(submission).model_dump()
            )
        return JsonResponse(
            {
                "items": response_list,
                "count": count,
                "page": page,
                "page_size": page_size,
                "has_more": count > offset + page_size,
            },
            status=200,
        )


@method_decorator(accessible_for(roles={"admin", "instructor"}), name="get")
class SubmittedAssignmentDetailView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            submission = AssignmentSubmission.objects.select_related(
                "delivery__course_content__assignment",
                "delivery__enrollment__learner",
            ).get(
                id=kwargs["submission_id"],
                delivery__course_content__course_id=kwargs["course_id"],
                delivery__course_content__course__organization_id=kwargs["organization_id"],
            )
            return JsonResponse(
                serializers.AssignmentSubmissionResponse.from_django_model(
                    submission,
                    request=request,
                ).model_dump(),
                status=200,
            )
        except AssignmentSubmission.DoesNotExist:
            return JsonResponse({"error": "Assignment submission not found"}, status=404)


@method_decorator(accessible_for(roles={"admin", "instructor"}), name="post")
class SubmissionReview(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.ReviewRquest.model_validate(payload)
            submission = AssignmentSubmission.objects.get(id=kwargs["submission_id"])
            initial_status = submission.status
            if submission.delivery.course_content.course.organization_id != kwargs["organization_id"]:
                return JsonResponse({"error": "Unauthorized"}, status=401)
            org_user = OrganizationUser.objects.filter(
                organization_id=kwargs["organization_id"], user_id=request.user.id
            ).first()
            if not org_user:
                return JsonResponse({"error": "Unauthorized"}, status=401)
            submission.status = serializer.review_result
            submission.reviewed_at = timezone.now()
            submission.reviewer = org_user
            submission.save()

            if serializer.comment is not None:
                if org_user.can_act_as_instructor():
                    AssignmentFeedback.objects.create(
                        submission=submission,
                        comment=serializer.comment,
                        provided_by=org_user,
                    )
                else:
                    logger.warning(
                        f"User {request.user.id} can not act as instructor, feedback not saved"
                        f" for submission {submission.id}, but status was updated to {submission.status}"
                    )

            # Send assignment review email
            if submission.status != initial_status or serializer.comment is not None:
                try:
                    SendAssignmentReviewCommand(
                        submission=submission,
                        include_last_feedback=serializer.comment is not None,
                    ).execute()
                except Exception as e:
                    logger.error(f"Failed to send assignment review email for submission {submission.id}: {str(e)}")

            return JsonResponse(
                serializers.AssignmentSubmissionResponse.from_django_model(
                    submission,
                    request=request,
                ).model_dump(),
                status=200,
            )
        except AssignmentSubmission.DoesNotExist:
            return JsonResponse({"error": "Assignment submission not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)
