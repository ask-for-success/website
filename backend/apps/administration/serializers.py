from rest_framework import serializers

from apps.audit.serializers import AuditRecordSerializer


class AccountOverviewSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    active = serializers.IntegerField()
    inactive = serializers.IntegerField()
    account_administrators = serializers.IntegerField()
    content_managers = serializers.IntegerField()
    hr_managers = serializers.IntegerField()


class MembershipOverviewSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    by_status = serializers.DictField(child=serializers.IntegerField())


class RecruitmentOverviewSerializer(serializers.Serializer):
    opportunities_total = serializers.IntegerField()
    open_opportunities = serializers.IntegerField()
    applications_total = serializers.IntegerField()
    applications_by_status = serializers.DictField(
        child=serializers.IntegerField()
    )


class EventOverviewSerializer(serializers.Serializer):
    upcoming = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    registered_participants = serializers.IntegerField()
    cancelled_registrations = serializers.IntegerField()
    checked_in = serializers.IntegerField()


class ContentTypeOverviewSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    by_status = serializers.DictField(child=serializers.IntegerField())


class AnnouncementOverviewSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    currently_visible = serializers.IntegerField()


class ContentOverviewSerializer(serializers.Serializer):
    news = ContentTypeOverviewSerializer()
    gallery_items = ContentTypeOverviewSerializer()
    gallery_videos = ContentTypeOverviewSerializer()
    member_announcements = AnnouncementOverviewSerializer()


class DonationOverviewSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    last_30_days = serializers.IntegerField()


class AuditOverviewSerializer(serializers.Serializer):
    last_30_days = serializers.IntegerField()
    recent_activity = AuditRecordSerializer(many=True)


class AdministrationOverviewSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    activity_window_days = serializers.IntegerField()
    accounts = AccountOverviewSerializer()
    memberships = MembershipOverviewSerializer()
    recruitment = RecruitmentOverviewSerializer()
    events = EventOverviewSerializer()
    content = ContentOverviewSerializer()
    donations = DonationOverviewSerializer()
    audit = AuditOverviewSerializer()
