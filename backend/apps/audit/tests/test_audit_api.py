from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.memberships.models import MembershipStatus, OnboardingStatus
from apps.memberships.operations import (
    admit_existing_account,
    record_member_departure,
    transfer_member,
    update_onboarding_status,
)
from apps.organization.models import Department, Position
from apps.recruitment.models import (
    ApplicationStatus,
    OpportunityStatus,
    RecruitmentApplication,
    RecruitmentForm,
    RecruitmentFormStatus,
    RecruitmentOpportunity,
)
from apps.recruitment.operations import change_application_status

from ..models import AuditAction, AuditDomain, AuditRecord
from ..services import record_audit_event


class AuditApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.account_administrator = User.objects.create_user(
            email="audit-admin@example.com",
            first_name="Audit",
            last_name="Administrator",
            phone_number="+212600001201",
            password="StrongPassword!2026",
        )
        cls.account_administrator.groups.add(
            Group.objects.get(name="account_administrator")
        )
        cls.hr_manager = User.objects.create_user(
            email="audit-hr@example.com",
            first_name="Audit",
            last_name="HR",
            phone_number="+212600001202",
            password="StrongPassword!2026",
        )
        cls.hr_manager.groups.add(Group.objects.get(name="content_manager"))
        cls.hr_manager.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="accounts",
                codename="manage_hr",
            )
        )
        cls.candidate = User.objects.create_user(
            email="audit-candidate@example.com",
            first_name="Audit",
            last_name="Candidate",
            phone_number="+212600001203",
            password="StrongPassword!2026",
        )
        cls.ordinary_user = User.objects.create_user(
            email="audit-ordinary@example.com",
            first_name="Audit",
            last_name="Ordinary",
            phone_number="+212600001204",
            password="StrongPassword!2026",
        )
        cls.engineering = Department.objects.create(name="Audit Engineering")
        cls.developer = Position.objects.create(
            department=cls.engineering,
            name="Audit Developer",
        )
        cls.marketing = Department.objects.create(name="Audit Marketing")
        cls.coordinator = Position.objects.create(
            department=cls.marketing,
            name="Audit Coordinator",
        )

    def admit_candidate(self):
        return admit_existing_account(
            user=self.candidate,
            department=self.engineering,
            position=self.developer,
            admitted_by=self.hr_manager,
        )

    def create_application(self):
        form = RecruitmentForm.objects.create(
            department=self.engineering,
            position=self.developer,
            name="Audit recruitment form",
            status=RecruitmentFormStatus.ACTIVE,
            created_by=self.hr_manager,
        )
        opportunity = RecruitmentOpportunity.objects.create(
            form=form,
            title="Audit recruitment opportunity",
            slug="audit-recruitment-opportunity",
            summary="Audit the recruitment lifecycle.",
            description_markdown="## Audit recruitment",
            status=OpportunityStatus.PUBLISHED,
            created_by=self.hr_manager,
        )
        return RecruitmentApplication.objects.create(
            opportunity=opportunity,
            applicant=self.candidate,
        )

    def test_membership_lifecycle_creates_state_and_reason_records(self):
        membership = self.admit_candidate()
        update_onboarding_status(
            membership=membership,
            new_status=OnboardingStatus.IN_PROGRESS,
            updated_by=self.hr_manager,
        )
        update_onboarding_status(
            membership=membership,
            new_status=OnboardingStatus.COMPLETED,
            updated_by=self.hr_manager,
        )
        transfer_member(
            membership=membership,
            new_department=self.marketing,
            new_position=self.coordinator,
            assigned_by=self.hr_manager,
            reason="Moved to coordinate outreach",
        )
        record_member_departure(
            membership=membership,
            recorded_by=self.hr_manager,
            reason="Member completed their term",
        )

        records = AuditRecord.objects.filter(membership=membership)

        self.assertEqual(records.count(), 5)
        self.assertTrue(
            records.filter(action=AuditAction.MEMBERSHIP_CREATED).exists()
        )
        self.assertEqual(
            records.filter(
                action=AuditAction.ONBOARDING_STATUS_CHANGED
            ).count(),
            2,
        )
        transfer = records.get(action=AuditAction.MEMBERSHIP_TRANSFERRED)
        self.assertEqual(transfer.reason, "Moved to coordinate outreach")
        self.assertEqual(
            transfer.previous_state["department_id"],
            str(self.engineering.id),
        )
        self.assertEqual(
            transfer.new_state["department_id"],
            str(self.marketing.id),
        )
        departure = records.get(action=AuditAction.DEPARTURE_RECORDED)
        self.assertEqual(
            departure.new_state["membership_status"],
            MembershipStatus.INACTIVE,
        )

    def test_application_status_change_creates_recruitment_record(self):
        application = self.create_application()

        change_application_status(
            application=application,
            new_status=ApplicationStatus.UNDER_REVIEW,
            changed_by=self.hr_manager,
        )

        record = AuditRecord.objects.get(application=application)
        self.assertEqual(record.domain, AuditDomain.RECRUITMENT)
        self.assertEqual(
            record.action,
            AuditAction.APPLICATION_STATUS_CHANGED,
        )
        self.assertEqual(
            record.previous_state["application_status"],
            ApplicationStatus.SUBMITTED,
        )
        self.assertEqual(
            record.new_state["application_status"],
            ApplicationStatus.UNDER_REVIEW,
        )

    def test_acceptance_correlates_application_and_membership_audits(self):
        application = self.create_application()

        change_application_status(
            application=application,
            new_status=ApplicationStatus.ACCEPTED,
            changed_by=self.hr_manager,
        )

        application.refresh_from_db()
        membership = application.applicant.membership
        records = AuditRecord.objects.filter(
            application=application,
            membership=membership,
        )
        self.assertEqual(records.count(), 2)
        self.assertSetEqual(
            set(records.values_list("action", flat=True)),
            {
                AuditAction.MEMBERSHIP_CREATED,
                AuditAction.APPLICATION_STATUS_CHANGED,
            },
        )

    def test_only_account_administrator_can_list_and_filter_records(self):
        membership = self.admit_candidate()
        url = "/api/v1/audit/records/"

        self.client.force_authenticate(self.ordinary_user)
        ordinary_response = self.client.get(url)
        self.client.force_authenticate(self.hr_manager)
        hr_response = self.client.get(url)
        self.client.force_authenticate(self.account_administrator)
        administrator_response = self.client.get(
            url,
            {
                "domain": AuditDomain.MEMBERSHIP,
                "membership_id": str(membership.id),
            },
        )

        self.assertEqual(ordinary_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(hr_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(administrator_response.status_code, status.HTTP_200_OK)
        self.assertEqual(administrator_response.data["count"], 1)
        self.assertEqual(
            administrator_response.data["results"][0]["membership_id"],
            str(membership.id),
        )

    def test_audit_records_reject_secrets_and_are_read_only(self):
        membership = self.admit_candidate()

        with self.assertRaises(ValidationError):
            record_audit_event(
                domain=AuditDomain.MEMBERSHIP,
                action=AuditAction.MEMBERSHIP_CREATED,
                actor=self.hr_manager,
                membership=membership,
                new_state={"token_hash": "must-never-be-stored"},
            )

        record = AuditRecord.objects.get(
            membership=membership,
            action=AuditAction.MEMBERSHIP_CREATED,
        )
        record.reason = "Attempted modification"
        with self.assertRaises(ValidationError):
            record.save()
        with self.assertRaises(ValidationError):
            record.delete()

        self.client.force_authenticate(self.account_administrator)
        create_response = self.client.post(
            "/api/v1/audit/records/",
            {},
            format="json",
        )
        update_response = self.client.patch(
            f"/api/v1/audit/records/{record.id}/",
            {"reason": "Attempted API modification"},
            format="json",
        )
        self.assertEqual(
            create_response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            update_response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_schema_documents_audit_endpoints(self):
        response = self.client.get(
            "/api/schema/",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("/api/v1/audit/records/", response.data["paths"])
        self.assertIn(
            "/api/v1/audit/records/{record_id}/",
            response.data["paths"],
        )
