import json
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.models import Group, Permission
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.memberships.models import (
    MemberAssignment,
    Membership,
    MembershipOnboarding,
    MembershipStatus,
    OnboardingStatus,
)
from apps.organization.models import Department, Position

from ..models import (
    ApplicationCv,
    ApplicationStatus,
    DecisionEmailStatus,
    OfferResponse,
    OpportunityStatus,
    RecruitmentApplication,
    RecruitmentForm,
    RecruitmentFormStatus,
    RecruitmentOpportunity,
    RecruitmentQuestion,
    RecruitmentQuestionType,
)


def pdf_file(name="candidate-cv.pdf"):
    return SimpleUploadedFile(
        name,
        b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n%%EOF",
        content_type="application/pdf",
    )


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class RecruitmentApiTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_media_directory = TemporaryDirectory()
        cls.cv_field = ApplicationCv._meta.get_field("file")
        cls.original_cv_storage = cls.cv_field.storage
        cls.cv_field.storage = FileSystemStorage(
            location=cls.private_media_directory.name,
            base_url=None,
        )
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.cv_field.storage = cls.original_cv_storage
        cls.private_media_directory.cleanup()

    @classmethod
    def setUpTestData(cls):
        cls.hr_manager = User.objects.create_user(
            email="recruitment-hr@example.com",
            first_name="Recruitment",
            last_name="Manager",
            phone_number="+212600001001",
            password="StrongPassword!2026",
        )
        cls.hr_manager.groups.add(Group.objects.get(name="content_manager"))
        cls.hr_manager.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="accounts",
                codename="manage_hr",
            )
        )
        cls.content_manager = User.objects.create_user(
            email="recruitment-content@example.com",
            first_name="Content",
            last_name="Manager",
            phone_number="+212600001002",
            password="StrongPassword!2026",
        )
        cls.content_manager.groups.add(Group.objects.get(name="content_manager"))
        cls.candidate = User.objects.create_user(
            email="recruitment-candidate@example.com",
            first_name="Candidate",
            last_name="One",
            phone_number="+212600001003",
            password="StrongPassword!2026",
        )
        cls.other_user = User.objects.create_user(
            email="recruitment-other@example.com",
            first_name="Other",
            last_name="User",
            phone_number="+212600001004",
            password="StrongPassword!2026",
        )
        cls.department = Department.objects.create(name="Engineering")
        cls.position = Position.objects.create(
            department=cls.department,
            name="Backend developer",
        )
        cls.form = RecruitmentForm.objects.create(
            department=cls.department,
            position=cls.position,
            name="Backend developer application",
            status=RecruitmentFormStatus.ACTIVE,
            created_by=cls.hr_manager,
        )
        cls.question = RecruitmentQuestion.objects.create(
            form=cls.form,
            label="Why do you want to join this department?",
            question_type=RecruitmentQuestionType.LONG_TEXT,
            is_required=True,
            display_order=1,
        )
        cls.opportunity = RecruitmentOpportunity.objects.create(
            form=cls.form,
            title="Backend developer recruitment",
            slug="backend-developer-recruitment",
            summary="Join the engineering department.",
            description_markdown="## Role\n\nBuild reliable backend services.",
            status=OpportunityStatus.PUBLISHED,
            created_by=cls.hr_manager,
        )

    def application_payload(self):
        return {
            "answers": json.dumps(
                [
                    {
                        "question_id": str(self.question.id),
                        "value": "I want to support the association's systems.",
                    }
                ]
            ),
            "cv": pdf_file(),
        }

    def submit_application(self, user=None):
        self.client.force_authenticate(user or self.candidate)
        return self.client.post(
            (
                f"/api/v1/recruitment/opportunities/"
                f"{self.opportunity.id}/applications/"
            ),
            self.application_payload(),
            format="multipart",
        )

    def send_offer(self, application_id):
        self.client.force_authenticate(self.hr_manager)
        return self.client.patch(
            f"/api/v1/recruitment/applications/{application_id}/status/",
            {"status": ApplicationStatus.OFFER_PENDING},
            format="json",
        )

    def respond_to_offer(self, application_id, response, user=None):
        self.client.force_authenticate(user or self.candidate)
        return self.client.post(
            (
                f"/api/v1/recruitment/applications/{application_id}/"
                "offer-response/"
            ),
            {"response": response},
            format="json",
        )

    def test_hr_manager_creates_department_position_form_with_questions(self):
        marketing = Department.objects.create(name="Marketing")
        coordinator = Position.objects.create(
            department=marketing,
            name="Campaign coordinator",
        )
        self.client.force_authenticate(self.hr_manager)

        response = self.client.post(
            "/api/v1/recruitment/forms/",
            {
                "name": "Campaign coordinator application",
                "description": "Questions for campaign candidates.",
                "status": RecruitmentFormStatus.ACTIVE,
                "department_id": str(marketing.id),
                "position_id": str(coordinator.id),
                "questions": [
                    {
                        "label": "Can you attend weekend activities?",
                        "help_text": "Select one answer.",
                        "question_type": RecruitmentQuestionType.YES_NO,
                        "is_required": True,
                        "display_order": 1,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_form = RecruitmentForm.objects.get(pk=response.data["id"])
        self.assertEqual(created_form.department, marketing)
        self.assertEqual(created_form.position, coordinator)
        self.assertEqual(created_form.questions.count(), 1)

    def test_active_form_requires_at_least_one_question(self):
        marketing = Department.objects.create(name="Communications")
        position = Position.objects.create(
            department=marketing,
            name="Writer",
        )
        self.client.force_authenticate(self.hr_manager)

        response = self.client.post(
            "/api/v1/recruitment/forms/",
            {
                "name": "Writer application",
                "status": RecruitmentFormStatus.ACTIVE,
                "department_id": str(marketing.id),
                "position_id": str(position.id),
                "questions": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("questions", response.data)

    def test_public_sees_only_published_opportunities_and_hr_sees_drafts(self):
        RecruitmentOpportunity.objects.create(
            form=self.form,
            title="Draft recruitment",
            slug="draft-recruitment",
            summary="Not public yet.",
            description_markdown="Draft",
            status=OpportunityStatus.DRAFT,
            created_by=self.hr_manager,
        )

        public_response = self.client.get("/api/v1/recruitment/opportunities/")
        self.client.force_authenticate(self.hr_manager)
        hr_response = self.client.get("/api/v1/recruitment/opportunities/")

        self.assertEqual(public_response.status_code, status.HTTP_200_OK)
        self.assertEqual(public_response.data["count"], 1)
        self.assertEqual(hr_response.data["count"], 2)

    def test_candidate_submits_answers_and_private_pdf_cv(self):
        response = self.submit_application()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        application = RecruitmentApplication.objects.get(applicant=self.candidate)
        self.assertEqual(application.answers.count(), 1)
        self.assertEqual(application.cv.content_type, "application/pdf")
        self.assertTrue(application.cv.file.name.startswith("recruitment/cvs/"))
        self.assertNotIn("/media/", response.data["cv"]["download_url"])
        self.assertIn(
            f"/api/v1/recruitment/applications/{application.id}/cv/",
            response.data["cv"]["download_url"],
        )

    def test_application_rejects_missing_required_answer_and_invalid_cv(self):
        self.client.force_authenticate(self.candidate)

        response = self.client.post(
            (
                f"/api/v1/recruitment/opportunities/"
                f"{self.opportunity.id}/applications/"
            ),
            {
                "answers": "[]",
                "cv": SimpleUploadedFile(
                    "candidate.txt",
                    b"not a pdf",
                    content_type="text/plain",
                ),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cv", response.data)
        self.assertFalse(
            RecruitmentApplication.objects.filter(applicant=self.candidate).exists()
        )

    def test_rejected_candidate_cannot_reapply_to_same_opportunity(self):
        first_response = self.submit_application()
        application = RecruitmentApplication.objects.get(
            pk=first_response.data["id"]
        )
        application.status = ApplicationStatus.REJECTED
        application.save(update_fields=("status", "updated_at"))

        second_response = self.submit_application()

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            second_response.data["opportunity"][0],
            (
                "You already applied to this opportunity. Apply to a new "
                "opportunity for a later recruitment campaign."
            ),
        )
        self.assertEqual(
            RecruitmentApplication.objects.filter(applicant=self.candidate).count(),
            1,
        )

    def test_rejected_candidate_can_apply_to_new_campaign_opportunity(self):
        first_response = self.submit_application()
        application = RecruitmentApplication.objects.get(
            pk=first_response.data["id"]
        )
        application.status = ApplicationStatus.REJECTED
        application.save(update_fields=("status", "updated_at"))
        later_opportunity = RecruitmentOpportunity.objects.create(
            form=self.form,
            title="Backend developer recruitment 2027",
            slug="backend-developer-recruitment-2027",
            summary="Join the next engineering recruitment campaign.",
            description_markdown="## Role\n\nA new campaign for the same role.",
            status=OpportunityStatus.PUBLISHED,
            created_by=self.hr_manager,
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.post(
            (
                f"/api/v1/recruitment/opportunities/"
                f"{later_opportunity.id}/applications/"
            ),
            self.application_payload(),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            RecruitmentApplication.objects.filter(
                applicant=self.candidate
            ).count(),
            2,
        )

    def test_archived_form_stops_new_applications(self):
        self.form.status = RecruitmentFormStatus.ARCHIVED
        self.form.save(update_fields=("status", "updated_at"))

        response = self.submit_application()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            RecruitmentApplication.objects.filter(applicant=self.candidate).exists()
        )

    def test_form_questions_lock_after_first_application(self):
        self.submit_application()
        self.client.force_authenticate(self.hr_manager)

        response = self.client.patch(
            f"/api/v1/recruitment/forms/{self.form.id}/",
            {
                "questions": [
                    {
                        "label": "A changed question",
                        "question_type": RecruitmentQuestionType.SHORT_TEXT,
                        "is_required": True,
                        "display_order": 1,
                    }
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.question.refresh_from_db()
        self.assertNotEqual(self.question.label, "A changed question")

    def test_hr_dashboard_and_detail_show_candidate_answers_and_cv(self):
        creation = self.submit_application()
        application_id = creation.data["id"]
        self.client.force_authenticate(self.hr_manager)

        list_response = self.client.get(
            "/api/v1/recruitment/applications/",
            {
                "department_id": str(self.department.id),
                "search": "candidate",
            },
        )
        detail_response = self.client.get(
            f"/api/v1/recruitment/applications/{application_id}/"
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["applicant"]["email"], self.candidate.email)
        self.assertEqual(len(detail_response.data["answers"]), 1)
        self.assertIn("download_url", detail_response.data["cv"])

    def test_general_content_manager_cannot_access_hr_applications(self):
        self.client.force_authenticate(self.content_manager)

        response = self.client.get("/api/v1/recruitment/applications/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cv_is_available_only_to_applicant_or_hr(self):
        creation = self.submit_application()
        cv_url = creation.data["cv"]["download_url"]
        cv_path = cv_url.replace("http://testserver", "")

        owner_response = self.client.get(cv_path)
        self.client.force_authenticate(self.other_user)
        denied_response = self.client.get(cv_path)
        self.client.force_authenticate(self.hr_manager)
        hr_response = self.client.get(cv_path)

        self.assertEqual(owner_response.status_code, status.HTTP_200_OK)
        self.assertEqual(denied_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(hr_response.status_code, status.HTTP_200_OK)
        self.assertEqual(hr_response["Cache-Control"], "private, no-store")

    def test_intermediate_status_does_not_send_email(self):
        creation = self.submit_application()
        self.client.force_authenticate(self.hr_manager)

        response = self.client.patch(
            (
                f"/api/v1/recruitment/applications/"
                f"{creation.data['id']}/status/"
            ),
            {"status": ApplicationStatus.INTERVIEW},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], ApplicationStatus.INTERVIEW)
        self.assertEqual(response.data["decision_email_status"], "not_required")
        self.assertEqual(len(mail.outbox), 0)

    def test_offer_does_not_create_membership_until_candidate_accepts(self):
        creation = self.submit_application()

        offer_response = self.send_offer(creation.data["id"])

        self.assertEqual(offer_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            offer_response.data["status"],
            ApplicationStatus.OFFER_PENDING,
        )
        self.assertEqual(
            offer_response.data["offer_email_status"],
            DecisionEmailStatus.SENT,
        )
        self.assertFalse(Membership.objects.filter(user=self.candidate).exists())
        self.assertEqual(len(mail.outbox), 1)

        acceptance_response = self.respond_to_offer(
            creation.data["id"],
            OfferResponse.ACCEPT,
        )

        self.assertEqual(acceptance_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            acceptance_response.data["status"],
            ApplicationStatus.ACCEPTED,
        )
        membership = Membership.objects.get(user=self.candidate)
        self.assertEqual(membership.status, MembershipStatus.PENDING_ONBOARDING)
        self.assertEqual(
            membership.assignments.get(ends_at__isnull=True).department,
            self.department,
        )
        self.assertEqual(len(mail.outbox), 2)

    def test_candidate_declines_offer_without_closing_other_applications(self):
        creation = self.submit_application()
        other_opportunity = RecruitmentOpportunity.objects.create(
            form=self.form,
            title="Alternative engineering opportunity",
            slug="alternative-engineering-opportunity",
            summary="An alternative opportunity.",
            description_markdown="## Alternative role",
            status=OpportunityStatus.PUBLISHED,
            created_by=self.hr_manager,
        )
        other_application = RecruitmentApplication.objects.create(
            opportunity=other_opportunity,
            applicant=self.candidate,
            status=ApplicationStatus.UNDER_REVIEW,
        )
        self.send_offer(creation.data["id"])

        response = self.respond_to_offer(
            creation.data["id"],
            OfferResponse.DECLINE,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["status"],
            ApplicationStatus.DECLINED_BY_CANDIDATE,
        )
        self.assertFalse(Membership.objects.filter(user=self.candidate).exists())
        other_application.refresh_from_db()
        self.assertEqual(
            other_application.status,
            ApplicationStatus.UNDER_REVIEW,
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_acceptance_withdraws_candidates_other_open_applications(self):
        creation = self.submit_application()
        other_opportunity = RecruitmentOpportunity.objects.create(
            form=self.form,
            title="Second engineering opportunity",
            slug="second-engineering-opportunity",
            summary="Another opportunity.",
            description_markdown="## Second role",
            status=OpportunityStatus.PUBLISHED,
            created_by=self.hr_manager,
        )
        other_application = RecruitmentApplication.objects.create(
            opportunity=other_opportunity,
            applicant=self.candidate,
            status=ApplicationStatus.INTERVIEW,
        )
        self.send_offer(creation.data["id"])

        response = self.respond_to_offer(
            creation.data["id"],
            OfferResponse.ACCEPT,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        other_application.refresh_from_db()
        self.assertEqual(other_application.status, ApplicationStatus.WITHDRAWN)
        self.assertEqual(other_application.decision_by, self.candidate)
        self.assertIsNotNone(other_application.decided_at)

    def test_another_account_cannot_respond_to_candidates_offer(self):
        creation = self.submit_application()
        self.send_offer(creation.data["id"])

        response = self.respond_to_offer(
            creation.data["id"],
            OfferResponse.ACCEPT,
            user=self.other_user,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        application = RecruitmentApplication.objects.get(pk=creation.data["id"])
        self.assertEqual(application.status, ApplicationStatus.OFFER_PENDING)

    def test_rejection_sends_email_without_creating_membership(self):
        creation = self.submit_application()
        self.client.force_authenticate(self.hr_manager)

        response = self.client.patch(
            (
                f"/api/v1/recruitment/applications/"
                f"{creation.data['id']}/status/"
            ),
            {"status": ApplicationStatus.REJECTED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Membership.objects.filter(user=self.candidate).exists())
        self.assertEqual(response.data["decision_email_status"], DecisionEmailStatus.SENT)
        self.assertEqual(len(mail.outbox), 1)

    def test_email_failure_does_not_reverse_final_decision(self):
        creation = self.submit_application()
        self.client.force_authenticate(self.hr_manager)

        with patch(
            "apps.recruitment.operations.EmailMessage.send",
            side_effect=RuntimeError("Email provider unavailable"),
        ):
            response = self.client.patch(
                (
                    f"/api/v1/recruitment/applications/"
                    f"{creation.data['id']}/status/"
                ),
                {"status": ApplicationStatus.REJECTED},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application = RecruitmentApplication.objects.get(pk=creation.data["id"])
        self.assertEqual(application.status, ApplicationStatus.REJECTED)
        self.assertEqual(application.decision_email_status, DecisionEmailStatus.FAILED)

    def test_offer_email_failure_does_not_cancel_outstanding_offer(self):
        creation = self.submit_application()
        self.client.force_authenticate(self.hr_manager)

        with patch(
            "apps.recruitment.operations.EmailMessage.send",
            side_effect=RuntimeError("Email provider unavailable"),
        ):
            response = self.client.patch(
                (
                    f"/api/v1/recruitment/applications/"
                    f"{creation.data['id']}/status/"
                ),
                {"status": ApplicationStatus.OFFER_PENDING},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application = RecruitmentApplication.objects.get(pk=creation.data["id"])
        self.assertEqual(application.status, ApplicationStatus.OFFER_PENDING)
        self.assertEqual(application.offer_email_status, DecisionEmailStatus.FAILED)

    def test_final_decision_cannot_change(self):
        creation = self.submit_application()
        status_url = (
            f"/api/v1/recruitment/applications/{creation.data['id']}/status/"
        )
        self.client.force_authenticate(self.hr_manager)
        self.client.patch(
            status_url,
            {"status": ApplicationStatus.REJECTED},
            format="json",
        )

        response = self.client.patch(
            status_url,
            {"status": ApplicationStatus.INTERVIEW},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 1)

    def test_former_member_is_reactivated_without_repeating_onboarding(self):
        membership = Membership.objects.create(
            user=self.candidate,
            status=MembershipStatus.INACTIVE,
        )
        onboarding = MembershipOnboarding.objects.create(
            membership=membership,
            status=OnboardingStatus.COMPLETED,
            started_at=timezone.now(),
            completed_at=timezone.now(),
        )
        creation = self.submit_application()
        self.send_offer(creation.data["id"])

        response = self.respond_to_offer(
            creation.data["id"],
            OfferResponse.ACCEPT,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        membership.refresh_from_db()
        onboarding.refresh_from_db()
        self.assertEqual(membership.status, MembershipStatus.ACTIVE)
        self.assertEqual(onboarding.status, OnboardingStatus.COMPLETED)
        self.assertEqual(membership.assignments.filter(ends_at__isnull=True).count(), 1)

    def test_current_member_accepts_offer_but_requires_explicit_transfer(self):
        membership = Membership.objects.create(
            user=self.candidate,
            status=MembershipStatus.ACTIVE,
        )
        MembershipOnboarding.objects.create(
            membership=membership,
            status=OnboardingStatus.COMPLETED,
            started_at=timezone.now(),
            completed_at=timezone.now(),
        )
        current_assignment = MemberAssignment.objects.create(
            membership=membership,
            department=self.department,
            position=self.position,
            assigned_by=self.hr_manager,
        )
        other_department = Department.objects.create(name="Product")
        other_position = Position.objects.create(
            department=other_department,
            name="Product coordinator",
        )
        other_form = RecruitmentForm.objects.create(
            department=other_department,
            position=other_position,
            name="Product application",
            status=RecruitmentFormStatus.ACTIVE,
            created_by=self.hr_manager,
        )
        other_opportunity = RecruitmentOpportunity.objects.create(
            form=other_form,
            title="Product recruitment",
            slug="product-recruitment",
            summary="Join product.",
            description_markdown="## Product",
            status=OpportunityStatus.PUBLISHED,
            created_by=self.hr_manager,
        )
        application = RecruitmentApplication.objects.create(
            opportunity=other_opportunity,
            applicant=self.candidate,
        )
        self.send_offer(application.id)

        response = self.respond_to_offer(application.id, OfferResponse.ACCEPT)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], ApplicationStatus.ACCEPTED)
        self.assertTrue(response.data["requires_department_transfer"])
        membership.refresh_from_db()
        self.assertEqual(membership.status, MembershipStatus.ACTIVE)
        self.assertEqual(
            membership.assignments.get(ends_at__isnull=True).id,
            current_assignment.id,
        )

    def test_hr_cannot_directly_mark_application_as_accepted(self):
        creation = self.submit_application()
        self.client.force_authenticate(self.hr_manager)

        response = self.client.patch(
            (
                f"/api/v1/recruitment/applications/"
                f"{creation.data['id']}/status/"
            ),
            {"status": ApplicationStatus.ACCEPTED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Membership.objects.filter(user=self.candidate).exists())

    def test_schema_documents_recruitment_routes(self):
        response = self.client.get(
            "/api/schema/",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("/api/v1/recruitment/forms/", response.data["paths"])
        self.assertIn(
            "/api/v1/recruitment/opportunities/{opportunity_id}/applications/",
            response.data["paths"],
        )
        self.assertIn(
            "/api/v1/recruitment/applications/{application_id}/status/",
            response.data["paths"],
        )
        self.assertIn(
            "/api/v1/recruitment/applications/{application_id}/offer-response/",
            response.data["paths"],
        )
