from datetime import timedelta

from django.contrib.auth.models import Group
from django.db.models import Count, Q
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.roles import ACCOUNT_ADMINISTRATOR, CONTENT_MANAGER
from apps.audit.models import AuditRecord
from apps.content.models import (
    GalleryItem,
    GalleryVideo,
    MemberAnnouncement,
    NewsArticle,
    PublicationStatus as ContentPublicationStatus,
)
from apps.donations.models import DonationSubmission
from apps.events.models import (
    Event,
    EventCheckIn,
    EventRegistration,
    EventRegistrationStatus,
    PublicationStatus as EventPublicationStatus,
)
from apps.memberships.models import Membership, MembershipStatus
from apps.recruitment.models import (
    ApplicationStatus,
    OpportunityStatus,
    RecruitmentApplication,
    RecruitmentOpportunity,
)


ACTIVITY_WINDOW_DAYS = 30
RECENT_ACTIVITY_LIMIT = 10


def counts_by_choice(queryset, field_name, choices) -> dict[str, int]:
    rows = queryset.values(field_name).annotate(total=Count("id"))
    available = {row[field_name]: row["total"] for row in rows}
    return {value: available.get(value, 0) for value, _label in choices}


def account_overview() -> dict:
    base = User.objects.all()
    active = base.filter(is_active=True)
    account_administrator_group = Group.objects.get(name=ACCOUNT_ADMINISTRATOR)
    content_manager_group = Group.objects.get(name=CONTENT_MANAGER)
    return {
        "total": base.count(),
        "active": active.count(),
        "inactive": base.filter(is_active=False).count(),
        "account_administrators": active.filter(
            groups=account_administrator_group
        ).count(),
        "content_managers": active.filter(groups=content_manager_group).count(),
        "hr_managers": active.filter(
            groups=content_manager_group,
            user_permissions__content_type__app_label="accounts",
            user_permissions__codename="manage_hr",
        ).distinct().count(),
    }


def membership_overview() -> dict:
    queryset = Membership.objects.all()
    return {
        "total": queryset.count(),
        "by_status": counts_by_choice(
            queryset,
            "status",
            MembershipStatus.choices,
        ),
    }


def recruitment_overview(now) -> dict:
    opportunities = RecruitmentOpportunity.objects.all()
    applications = RecruitmentApplication.objects.all()
    open_opportunities = opportunities.filter(
        status=OpportunityStatus.PUBLISHED,
    ).filter(
        Q(opens_at__isnull=True) | Q(opens_at__lte=now),
        Q(closes_at__isnull=True) | Q(closes_at__gt=now),
    )
    return {
        "opportunities_total": opportunities.count(),
        "open_opportunities": open_opportunities.count(),
        "applications_total": applications.count(),
        "applications_by_status": counts_by_choice(
            applications,
            "status",
            ApplicationStatus.choices,
        ),
    }


def event_overview(now) -> dict:
    return {
        "upcoming": Event.objects.filter(
            publication_status=EventPublicationStatus.PUBLISHED,
            starts_at__gte=now,
        ).count(),
        "cancelled": Event.objects.filter(
            publication_status=EventPublicationStatus.CANCELLED,
        ).count(),
        "registered_participants": EventRegistration.objects.filter(
            status=EventRegistrationStatus.REGISTERED,
        ).count(),
        "cancelled_registrations": EventRegistration.objects.filter(
            status=EventRegistrationStatus.CANCELLED,
        ).count(),
        "checked_in": EventCheckIn.objects.count(),
    }


def content_type_overview(model) -> dict:
    queryset = model.objects.all()
    return {
        "total": queryset.count(),
        "by_status": counts_by_choice(
            queryset,
            "publication_status",
            ContentPublicationStatus.choices,
        ),
    }


def content_overview() -> dict:
    announcements = MemberAnnouncement.objects.all()
    return {
        "news": content_type_overview(NewsArticle),
        "gallery_items": content_type_overview(GalleryItem),
        "gallery_videos": content_type_overview(GalleryVideo),
        "member_announcements": {
            "total": announcements.count(),
            "currently_visible": announcements.visible_to_members().count(),
        },
    }


def build_administration_overview() -> dict:
    now = timezone.now()
    activity_start = now - timedelta(days=ACTIVITY_WINDOW_DAYS)
    audit_queryset = AuditRecord.objects.select_related("actor")
    recent_activity = list(audit_queryset[:RECENT_ACTIVITY_LIMIT])
    return {
        "generated_at": now,
        "activity_window_days": ACTIVITY_WINDOW_DAYS,
        "accounts": account_overview(),
        "memberships": membership_overview(),
        "recruitment": recruitment_overview(now),
        "events": event_overview(now),
        "content": content_overview(),
        "donations": {
            "total": DonationSubmission.objects.count(),
            "last_30_days": DonationSubmission.objects.filter(
                created_at__gte=activity_start,
            ).count(),
        },
        "audit": {
            "last_30_days": audit_queryset.filter(
                created_at__gte=activity_start,
            ).count(),
            "recent_activity": recent_activity,
        },
    }
