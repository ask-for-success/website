from datetime import timedelta

from django.contrib.auth.models import Group, Permission
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.roles import ACCOUNT_ADMINISTRATOR, CONTENT_MANAGER
from apps.audit.models import AuditAction, AuditDomain
from apps.audit.services import record_audit_event
from apps.content.models import (
    ContentCategory,
    ContentSection,
    GalleryItem,
    GalleryVideo,
    MemberAnnouncement,
    NewsArticle,
    PublicationStatus as ContentPublicationStatus,
)
from apps.donations.models import DonationSubmission, DonationType
from apps.events.models import (
    Event,
    EventCheckIn,
    EventRegistration,
    EventRegistrationStatus,
    EventTicket,
    PublicationStatus as EventPublicationStatus,
)
from apps.memberships.models import Membership, MembershipStatus
from apps.organization.models import Department, Position
from apps.recruitment.models import (
    ApplicationStatus,
    OpportunityStatus,
    RecruitmentApplication,
    RecruitmentForm,
    RecruitmentOpportunity,
)


class AdministrationOverviewApiTests(APITestCase):
    overview_url = "/api/v1/administration/overview/"
    schema_url = "/api/schema/"

    @classmethod
    def setUpTestData(cls):
        cls.administrator = User.objects.create_user(
            email="overview-admin@example.com",
            first_name="Overview",
            last_name="Administrator",
            phone_number="+212600008001",
            password="StrongPassword!2026",
        )
        cls.administrator.groups.add(
            Group.objects.get(name=ACCOUNT_ADMINISTRATOR)
        )
        cls.regular_user = User.objects.create_user(
            email="overview-user@example.com",
            first_name="Overview",
            last_name="User",
            phone_number="+212600008002",
            password="StrongPassword!2026",
        )

    def test_overview_requires_account_administrator_access(self):
        anonymous = self.client.get(self.overview_url)
        self.client.force_authenticate(self.regular_user)
        regular = self.client.get(self.overview_url)

        self.assertEqual(anonymous.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(regular.status_code, status.HTTP_403_FORBIDDEN)

    def test_administrator_receives_complete_empty_safe_structure(self):
        self.client.force_authenticate(self.administrator)

        response = self.client.get(self.overview_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["activity_window_days"], 30)
        self.assertEqual(response.data["accounts"]["total"], 2)
        self.assertEqual(response.data["memberships"]["total"], 0)
        self.assertEqual(response.data["recruitment"]["applications_total"], 0)
        self.assertEqual(response.data["events"]["upcoming"], 0)
        self.assertEqual(response.data["content"]["news"]["total"], 0)
        self.assertEqual(response.data["donations"]["total"], 0)
        self.assertEqual(response.data["audit"]["recent_activity"], [])

    def test_overview_aggregates_current_cross_domain_state(self):
        now = timezone.now()
        manager = User.objects.create_user(
            email="overview-manager@example.com",
            first_name="Content",
            last_name="Manager",
            phone_number="+212600008003",
            password="StrongPassword!2026",
        )
        manager.groups.add(Group.objects.get(name=CONTENT_MANAGER))
        manager.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="accounts",
                codename="manage_hr",
            )
        )
        inactive = User.objects.create_user(
            email="overview-inactive@example.com",
            first_name="Inactive",
            last_name="Account",
            phone_number="+212600008004",
            password="StrongPassword!2026",
            is_active=False,
        )
        Membership.objects.create(
            user=self.regular_user,
            status=MembershipStatus.ACTIVE,
        )
        Membership.objects.create(
            user=inactive,
            status=MembershipStatus.INACTIVE,
        )
        department = Department.objects.create(
            name="Overview Department",
            description="Dashboard test department.",
        )
        position = Position.objects.create(
            department=department,
            name="Overview Position",
            description="Dashboard test position.",
        )
        form = RecruitmentForm.objects.create(
            department=department,
            position=position,
            name="Overview Form",
            created_by=manager,
        )
        opportunity = RecruitmentOpportunity.objects.create(
            form=form,
            title="Overview Opportunity",
            slug="overview-opportunity",
            summary="Overview opportunity summary.",
            description_markdown="Overview opportunity.",
            status=OpportunityStatus.PUBLISHED,
            opens_at=now - timedelta(days=1),
            closes_at=now + timedelta(days=1),
            created_by=manager,
        )
        RecruitmentApplication.objects.create(
            opportunity=opportunity,
            applicant=self.regular_user,
            status=ApplicationStatus.UNDER_REVIEW,
        )
        event = Event.objects.create(
            title="Overview Event",
            summary="Overview event.",
            description="Overview event description.",
            location="Casablanca",
            starts_at=now + timedelta(days=2),
            ends_at=now + timedelta(days=2, hours=2),
            publication_status=EventPublicationStatus.PUBLISHED,
            requires_qr_code=True,
            created_by=manager,
        )
        registration = EventRegistration.objects.create(
            event=event,
            email="participant@example.com",
        )
        ticket = EventTicket.objects.create(
            registration=registration,
            qr_code_hash="a" * 64,
        )
        EventCheckIn.objects.create(ticket=ticket, checked_in_by=manager)
        EventRegistration.objects.create(
            event=event,
            email="cancelled@example.com",
            status=EventRegistrationStatus.CANCELLED,
        )
        category_news = ContentCategory.objects.create(
            section=ContentSection.NEWS,
            name="Overview News",
            slug="overview-news",
            created_by=manager,
            updated_by=manager,
        )
        category_gallery = ContentCategory.objects.create(
            section=ContentSection.GALLERY,
            name="Overview Gallery",
            slug="overview-gallery",
            created_by=manager,
            updated_by=manager,
        )
        NewsArticle.objects.create(
            category=category_news,
            title="Overview Article",
            slug="overview-article",
            excerpt="Overview article excerpt.",
            body_markdown="Overview article body.",
            cover_image="content/news/overview-article.jpg",
            cover_alt_text="Overview article",
            publication_status=ContentPublicationStatus.DRAFT,
            created_by=manager,
            updated_by=manager,
        )
        GalleryItem.objects.create(
            category=category_gallery,
            image="content/gallery/overview-gallery.jpg",
            alt_text="Overview gallery item",
            publication_status=ContentPublicationStatus.PUBLISHED,
            published_at=now,
            created_by=manager,
            updated_by=manager,
        )
        GalleryVideo.objects.create(
            title="Overview Video",
            youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            publication_status=ContentPublicationStatus.SCHEDULED,
            published_at=now + timedelta(days=1),
            created_by=manager,
            updated_by=manager,
        )
        MemberAnnouncement.objects.create(
            title="Overview Announcement",
            message="Overview announcement message.",
            created_by=manager,
            updated_by=manager,
        )
        DonationSubmission.objects.create(
            first_name="Overview",
            last_name="Donor",
            email="donor@example.com",
            phone_number="+212600008010",
            donation_type=DonationType.GOODS,
            details="Books.",
        )
        record_audit_event(
            domain=AuditDomain.ACCOUNTS,
            action=AuditAction.ACCOUNT_LOGIN,
            actor=manager,
            target_type="user",
            target_id=manager.id,
        )
        self.client.force_authenticate(self.administrator)

        response = self.client.get(self.overview_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["accounts"]["total"], 4)
        self.assertEqual(response.data["accounts"]["inactive"], 1)
        self.assertEqual(response.data["accounts"]["content_managers"], 1)
        self.assertEqual(response.data["accounts"]["hr_managers"], 1)
        self.assertEqual(response.data["memberships"]["total"], 2)
        self.assertEqual(response.data["memberships"]["by_status"]["active"], 1)
        self.assertEqual(
            response.data["memberships"]["by_status"]["inactive"],
            1,
        )
        self.assertEqual(response.data["recruitment"]["open_opportunities"], 1)
        self.assertEqual(
            response.data["recruitment"]["applications_by_status"][
                "under_review"
            ],
            1,
        )
        self.assertEqual(response.data["events"]["upcoming"], 1)
        self.assertEqual(response.data["events"]["registered_participants"], 1)
        self.assertEqual(response.data["events"]["cancelled_registrations"], 1)
        self.assertEqual(response.data["events"]["checked_in"], 1)
        self.assertEqual(response.data["content"]["news"]["by_status"]["draft"], 1)
        self.assertEqual(
            response.data["content"]["gallery_items"]["by_status"][
                "published"
            ],
            1,
        )
        self.assertEqual(response.data["donations"]["last_30_days"], 1)
        self.assertEqual(response.data["audit"]["last_30_days"], 1)
        self.assertEqual(
            response.data["audit"]["recent_activity"][0]["actor_email"],
            manager.email,
        )
        response_text = str(response.data)
        self.assertNotIn("donor@example.com", response_text)
        self.assertNotIn("participant@example.com", response_text)
        self.assertNotIn("cancelled@example.com", response_text)

    def test_openapi_schema_contains_administration_overview(self):
        response = self.client.get(self.schema_url, HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.overview_url, response.data["paths"])
        self.assertEqual(
            response.data["paths"][self.overview_url]["get"]["tags"],
            ["Administration"],
        )
