import base64
from datetime import timedelta
from tempfile import TemporaryDirectory

from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.events.models import Event
from apps.memberships.models import Membership, MembershipStatus

from ..models import (
    AboutPage,
    AboutPillar,
    ContentCategory,
    ContentSection,
    DonationOption,
    EventsPage,
    GalleryItem,
    GalleryVideo,
    GetInvolvedPage,
    HomeFeature,
    HomePage,
    ImpactStatistic,
    InvolvementFeature,
    InvolvementStep,
    MemberAnnouncement,
    NewsArticle,
    PageSettings,
    PublicationStatus,
    SiteSettings,
)


TINY_GIF = base64.b64decode(
    "R0lGODlhAQABAIABAP///wAAACwAAAAAAQABAAACAkQBADs="
)


def image_file(name="image.gif"):
    return SimpleUploadedFile(name, TINY_GIF, content_type="image/gif")


class ContentApiTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        cls.media_directory = TemporaryDirectory()
        cls.media_override = override_settings(
            MEDIA_ROOT=cls.media_directory.name
        )
        cls.media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.media_override.disable()
        cls.media_directory.cleanup()

    @classmethod
    def setUpTestData(cls):
        cls.content_manager = User.objects.create_user(
            email="cms-manager@example.com",
            first_name="CMS",
            last_name="Manager",
            phone_number="+212600000701",
            password="StrongPassword!2026",
        )
        cls.content_manager.groups.add(Group.objects.get(name="content_manager"))
        cls.ordinary_user = User.objects.create_user(
            email="ordinary-content-user@example.com",
            first_name="Ordinary",
            last_name="User",
            phone_number="+212600000702",
            password="StrongPassword!2026",
        )
        Membership.objects.create(
            user=cls.ordinary_user,
            status=MembershipStatus.INACTIVE,
        )
        cls.active_member_user = User.objects.create_user(
            email="active-member@example.com",
            first_name="Active",
            last_name="Member",
            phone_number="+212600000703",
            password="StrongPassword!2026",
        )
        Membership.objects.create(
            user=cls.active_member_user,
            status=MembershipStatus.ACTIVE,
        )
        cls.news_category = ContentCategory.objects.get(
            section=ContentSection.NEWS,
            slug="events",
        )
        cls.gallery_category = ContentCategory.objects.get(
            section=ContentSection.GALLERY,
            slug="outreach",
        )

    def create_article(self, title, publication_status, published_at):
        slug = title.lower().replace(" ", "-")
        return NewsArticle.objects.create(
            category=self.news_category,
            title=title,
            slug=slug,
            excerpt=f"Excerpt for {title}",
            body_markdown=f"## {title}\n\nBody for {title}",
            cover_image=image_file(f"{slug}.gif"),
            cover_alt_text=f"Cover for {title}",
            publication_status=publication_status,
            published_at=published_at,
            created_by=self.content_manager,
            updated_by=self.content_manager,
        )

    def article_payload(self, **overrides):
        payload = {
            "category": str(self.news_category.id),
            "title": "New community story",
            "slug": "new-community-story",
            "excerpt": "A short card summary.",
            "body_markdown": (
                "## Community story\n\n"
                "The complete article content.\n\n"
                "![Volunteers working with students]"
                "(https://cdn.example.com/news/volunteers.jpg)"
            ),
            "cover_image": image_file("new-community-story.gif"),
            "cover_alt_text": "Volunteers working with students",
            "publication_status": PublicationStatus.PUBLISHED,
            "is_featured": False,
            "display_order": 1,
        }
        payload.update(overrides)
        return payload

    def create_event(self, title="Member event"):
        starts_at = timezone.now() + timedelta(days=7)
        return Event.objects.create(
            title=title,
            summary="An event for members.",
            description="Complete event information.",
            location="Casablanca",
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=2),
            created_by=self.content_manager,
        )

    def test_initial_page_settings_and_categories_match_the_design(self):
        news_page = PageSettings.objects.get(section=ContentSection.NEWS)
        gallery_page = PageSettings.objects.get(section=ContentSection.GALLERY)

        self.assertEqual(news_page.heading, "Latest articles")
        self.assertEqual(gallery_page.heading, "Moments that tell our story.")
        self.assertEqual(
            ContentCategory.objects.filter(section=ContentSection.NEWS).count(),
            4,
        )
        self.assertEqual(
            ContentCategory.objects.filter(section=ContentSection.GALLERY).count(),
            5,
        )

    def test_public_news_list_hides_non_public_articles(self):
        now = timezone.now()
        visible = self.create_article(
            "Published story",
            PublicationStatus.PUBLISHED,
            now - timedelta(hours=1),
        )
        due_schedule = self.create_article(
            "Due scheduled story",
            PublicationStatus.SCHEDULED,
            now - timedelta(minutes=1),
        )
        self.create_article("Draft story", PublicationStatus.DRAFT, None)
        self.create_article(
            "Future story",
            PublicationStatus.SCHEDULED,
            now + timedelta(days=1),
        )
        self.create_article(
            "Archived story",
            PublicationStatus.ARCHIVED,
            now - timedelta(days=1),
        )

        response = self.client.get("/api/v1/content/news/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(returned_ids, {str(visible.id), str(due_schedule.id)})

    def test_content_manager_can_list_drafts_and_filter_by_status(self):
        self.create_article("Draft story", PublicationStatus.DRAFT, None)
        self.create_article(
            "Published story",
            PublicationStatus.PUBLISHED,
            timezone.now(),
        )
        self.client.force_authenticate(self.content_manager)

        response = self.client.get(
            "/api/v1/content/news/",
            {"status": PublicationStatus.DRAFT},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["publication_status"],
            PublicationStatus.DRAFT,
        )

    def test_content_manager_creates_published_article_with_image(self):
        self.client.force_authenticate(self.content_manager)

        response = self.client.post(
            "/api/v1/content/news/",
            self.article_payload(),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        article = NewsArticle.objects.get(slug="new-community-story")
        self.assertEqual(article.created_by, self.content_manager)
        self.assertIsNotNone(article.published_at)
        self.assertTrue(article.cover_image.name.startswith("content/news/"))
        self.assertIn(
            "https://cdn.example.com/news/volunteers.jpg",
            article.body_markdown,
        )
        self.assertEqual(
            response.data["body_markdown"],
            article.body_markdown,
        )

    def test_ordinary_user_cannot_create_article(self):
        self.client.force_authenticate(self.ordinary_user)

        response = self.client.post(
            "/api/v1/content/news/",
            self.article_payload(),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(NewsArticle.objects.exists())

    def test_news_article_rejects_gallery_category(self):
        self.client.force_authenticate(self.content_manager)

        response = self.client.post(
            "/api/v1/content/news/",
            self.article_payload(category=str(self.gallery_category.id)),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", response.data)

    def test_page_settings_are_public_but_only_managers_can_update_them(self):
        public_response = self.client.get("/api/v1/content/pages/news/")
        self.client.force_authenticate(self.ordinary_user)
        denied_response = self.client.patch(
            "/api/v1/content/pages/news/",
            {"heading": "A denied change"},
            format="json",
        )
        self.client.force_authenticate(self.content_manager)
        update_response = self.client.patch(
            "/api/v1/content/pages/news/",
            {"heading": "News and stories"},
            format="json",
        )

        self.assertEqual(public_response.status_code, status.HTTP_200_OK)
        self.assertEqual(denied_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["heading"], "News and stories")
        self.assertEqual(
            PageSettings.objects.get(section=ContentSection.NEWS).updated_by,
            self.content_manager,
        )

    def test_public_gallery_supports_category_filtering(self):
        item = GalleryItem.objects.create(
            category=self.gallery_category,
            image=image_file("outreach.gif"),
            alt_text="Volunteers during an outreach day",
            caption="Atlas outreach day",
            publication_status=PublicationStatus.PUBLISHED,
            published_at=timezone.now() - timedelta(minutes=1),
            created_by=self.content_manager,
            updated_by=self.content_manager,
        )
        GalleryItem.objects.create(
            category=ContentCategory.objects.get(
                section=ContentSection.GALLERY,
                slug="workshops",
            ),
            image=image_file("workshop.gif"),
            alt_text="Students attending a workshop",
            caption="Student workshop",
            publication_status=PublicationStatus.PUBLISHED,
            published_at=timezone.now() - timedelta(minutes=1),
            created_by=self.content_manager,
            updated_by=self.content_manager,
        )

        response = self.client.get(
            "/api/v1/content/gallery/",
            {"category": "outreach"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(item.id))

    def test_schema_documents_content_routes(self):
        response = self.client.get(
            "/api/schema/",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("/api/v1/content/news/", response.data["paths"])
        self.assertIn("/api/v1/content/gallery/", response.data["paths"])
        self.assertIn("/api/v1/content/pages/news/", response.data["paths"])
        self.assertIn("/api/v1/content/pages/home/", response.data["paths"])
        self.assertIn("/api/v1/content/pages/about/", response.data["paths"])
        self.assertIn(
            "/api/v1/content/pages/get-involved/",
            response.data["paths"],
        )
        self.assertIn("/api/v1/content/pages/events/", response.data["paths"])
        self.assertIn(
            "/api/v1/content/gallery/videos/",
            response.data["paths"],
        )
        self.assertIn(
            "/api/v1/content/announcements/",
            response.data["paths"],
        )
        self.assertIn(
            "/api/v1/content/announcements/{announcement_id}/",
            response.data["paths"],
        )
        self.assertIn(
            "/api/v1/content/member-announcements/",
            response.data["paths"],
        )

    def test_structured_pages_are_seeded_from_the_approved_design(self):
        self.assertTrue(SiteSettings.objects.filter(site_key="main").exists())
        self.assertTrue(HomePage.objects.filter(page_key="home").exists())
        self.assertTrue(AboutPage.objects.filter(page_key="about").exists())
        self.assertTrue(
            GetInvolvedPage.objects.filter(page_key="get_involved").exists()
        )
        self.assertTrue(EventsPage.objects.filter(page_key="events").exists())
        self.assertEqual(ImpactStatistic.objects.count(), 4)
        self.assertEqual(HomeFeature.objects.count(), 3)
        self.assertEqual(AboutPillar.objects.count(), 4)
        self.assertEqual(InvolvementFeature.objects.count(), 8)
        self.assertEqual(DonationOption.objects.count(), 2)
        self.assertEqual(InvolvementStep.objects.count(), 4)

    def test_public_home_page_aggregates_active_typed_content(self):
        hidden_feature = HomeFeature.objects.order_by("display_order").first()
        hidden_feature.is_active = False
        hidden_feature.save(update_fields=("is_active", "updated_at"))

        response = self.client.get("/api/v1/content/pages/home/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["page_key"], "home")
        self.assertEqual(len(response.data["features"]), 2)
        self.assertEqual(len(response.data["impact_statistics"]), 4)

    def test_content_manager_sees_inactive_page_items(self):
        hidden_feature = HomeFeature.objects.order_by("display_order").first()
        hidden_feature.is_active = False
        hidden_feature.save(update_fields=("is_active", "updated_at"))
        self.client.force_authenticate(self.content_manager)

        response = self.client.get("/api/v1/content/pages/home/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["features"]), 3)

    def test_only_content_manager_can_update_structured_page(self):
        self.client.force_authenticate(self.ordinary_user)
        denied = self.client.patch(
            "/api/v1/content/pages/about/",
            {"mission_heading": "A denied update"},
            format="json",
        )
        self.client.force_authenticate(self.content_manager)
        accepted = self.client.patch(
            "/api/v1/content/pages/about/",
            {"mission_heading": "Creating access together"},
            format="json",
        )

        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(accepted.status_code, status.HTTP_200_OK)
        self.assertEqual(
            accepted.data["mission_heading"],
            "Creating access together",
        )
        self.assertEqual(
            AboutPage.objects.get(page_key="about").updated_by,
            self.content_manager,
        )

    def test_content_manager_creates_and_hides_ordered_page_item(self):
        self.client.force_authenticate(self.content_manager)
        creation = self.client.post(
            "/api/v1/content/about/pillars/",
            {
                "icon_key": "leadership",
                "title": "Leadership",
                "body": "Young people learn by leading real initiatives.",
                "display_order": 5,
                "is_active": True,
            },
            format="json",
        )
        item_id = creation.data["id"]
        update = self.client.patch(
            f"/api/v1/content/about/pillars/{item_id}/",
            {"is_active": False},
            format="json",
        )
        self.client.force_authenticate(user=None)
        public_list = self.client.get("/api/v1/content/about/pillars/")

        self.assertEqual(creation.status_code, status.HTTP_201_CREATED)
        self.assertEqual(update.status_code, status.HTTP_200_OK)
        self.assertNotIn(item_id, {item["id"] for item in public_list.data})

    def test_site_contact_settings_are_public_and_manager_editable(self):
        public_response = self.client.get("/api/v1/content/site/")
        self.client.force_authenticate(self.content_manager)
        update_response = self.client.patch(
            "/api/v1/content/site/",
            {
                "contact_email": "contact@askforsuccess.org",
                "contact_phone": "+212 6 12 34 56 78",
                "contact_location": "Casablanca, Morocco",
                "tiktok_url": "https://www.tiktok.com/@askforsuccess",
                "youtube_url": "https://www.youtube.com/@askforsuccess",
                "instagram_url": "https://www.instagram.com/askforsuccess",
                "linkedin_url": "https://www.linkedin.com/company/askforsuccess",
            },
            format="json",
        )

        self.assertEqual(public_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            update_response.data["contact_email"],
            "contact@askforsuccess.org",
        )
        self.assertEqual(
            update_response.data["contact_phone"],
            "+212 6 12 34 56 78",
        )
        self.assertEqual(
            update_response.data["instagram_url"],
            "https://www.instagram.com/askforsuccess",
        )

    def test_ordinary_account_cannot_update_footer_settings(self):
        self.client.force_authenticate(self.ordinary_user)

        response = self.client.patch(
            "/api/v1/content/site/",
            {"linkedin_url": "https://www.linkedin.com/company/denied"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_public_gallery_videos_hide_drafts(self):
        published = GalleryVideo.objects.create(
            title="Youth Summit aftermovie",
            youtube_url="https://www.youtube.com/watch?v=AbCdEfGhI12",
            thumbnail=image_file("summit-video.gif"),
            thumbnail_alt_text="Youth Summit participants",
            duration_label="3 min",
            publication_status=PublicationStatus.PUBLISHED,
            published_at=timezone.now(),
            created_by=self.content_manager,
            updated_by=self.content_manager,
        )
        GalleryVideo.objects.create(
            title="Draft video",
            youtube_url="https://youtu.be/ZyXwVuTsR98",
            thumbnail=image_file("draft-video.gif"),
            thumbnail_alt_text="Draft thumbnail",
            publication_status=PublicationStatus.DRAFT,
            created_by=self.content_manager,
            updated_by=self.content_manager,
        )

        response = self.client.get("/api/v1/content/gallery/videos/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(published.id))
        self.assertEqual(
            response.data["results"][0]["youtube_video_id"],
            "AbCdEfGhI12",
        )
        self.assertEqual(
            response.data["results"][0]["youtube_embed_url"],
            "https://www.youtube-nocookie.com/embed/AbCdEfGhI12",
        )

    def test_gallery_video_rejects_non_youtube_url(self):
        self.client.force_authenticate(self.content_manager)

        response = self.client.post(
            "/api/v1/content/gallery/videos/",
            {
                "title": "Externally hosted video",
                "youtube_url": "https://video.example.com/not-youtube",
                "thumbnail": image_file("external-video.gif"),
                "thumbnail_alt_text": "Video thumbnail",
                "publication_status": PublicationStatus.DRAFT,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("youtube_url", response.data)

    def test_gallery_video_normalizes_youtube_share_url(self):
        self.client.force_authenticate(self.content_manager)

        response = self.client.post(
            "/api/v1/content/gallery/videos/",
            {
                "title": "YouTube highlight",
                "youtube_url": "https://youtu.be/LmNoPqRsT34?t=12",
                "publication_status": PublicationStatus.DRAFT,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["youtube_url"],
            "https://www.youtube.com/watch?v=LmNoPqRsT34",
        )
        self.assertEqual(response.data["youtube_video_id"], "LmNoPqRsT34")
        self.assertIsNone(response.data["thumbnail"])
        self.assertEqual(
            response.data["youtube_thumbnail_url"],
            "https://i.ytimg.com/vi/LmNoPqRsT34/hqdefault.jpg",
        )

    def test_get_involved_page_returns_ordered_donation_and_process_content(self):
        response = self.client.get("/api/v1/content/pages/get-involved/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["donation_options"]), 2)
        self.assertEqual(len(response.data["steps"]), 4)
        self.assertEqual(response.data["steps"][0]["display_order"], 1)

    def test_content_manager_can_create_member_announcement(self):
        self.client.force_authenticate(self.content_manager)

        response = self.client.post(
            "/api/v1/content/announcements/",
            {
                "title": "Monthly member meeting",
                "message": "The member meeting starts at 18:00.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["state"], "active")
        announcement = MemberAnnouncement.objects.get(id=response.data["id"])
        self.assertEqual(announcement.created_by, self.content_manager)
        self.assertEqual(announcement.updated_by, self.content_manager)

    def test_announcement_can_reference_an_event(self):
        event = self.create_event()
        self.client.force_authenticate(self.content_manager)

        response = self.client.post(
            "/api/v1/content/announcements/",
            {
                "title": "Registration is open",
                "message": "Members can now register for this event.",
                "event": str(event.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data["event"]), str(event.id))
        self.assertEqual(response.data["event_title"], event.title)
        self.assertIsNone(response.data["article"])

    def test_announcement_rejects_event_and_article_together(self):
        event = self.create_event()
        article = self.create_article(
            "Member news",
            PublicationStatus.PUBLISHED,
            timezone.now(),
        )
        self.client.force_authenticate(self.content_manager)

        response = self.client.post(
            "/api/v1/content/announcements/",
            {
                "title": "Ambiguous reference",
                "message": "This must reference only one content item.",
                "event": str(event.id),
                "article": str(article.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("article", response.data)

    def test_announcement_rejects_expiration_before_publication(self):
        self.client.force_authenticate(self.content_manager)
        publication_time = timezone.now() + timedelta(days=2)

        response = self.client.post(
            "/api/v1/content/announcements/",
            {
                "title": "Invalid schedule",
                "message": "The expiration cannot precede publication.",
                "published_at": publication_time.isoformat(),
                "expires_at": (publication_time - timedelta(hours=1)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expires_at", response.data)

    def test_active_member_feed_only_returns_current_announcements(self):
        now = timezone.now()
        current = MemberAnnouncement.objects.create(
            title="Current announcement",
            message="Visible to active members.",
            published_at=now - timedelta(minutes=1),
            expires_at=now + timedelta(days=1),
            created_by=self.content_manager,
            updated_by=self.content_manager,
        )
        MemberAnnouncement.objects.create(
            title="Scheduled announcement",
            message="Not visible yet.",
            published_at=now + timedelta(days=1),
            created_by=self.content_manager,
            updated_by=self.content_manager,
        )
        MemberAnnouncement.objects.create(
            title="Expired announcement",
            message="No longer visible.",
            published_at=now - timedelta(days=2),
            expires_at=now - timedelta(days=1),
            created_by=self.content_manager,
            updated_by=self.content_manager,
        )
        MemberAnnouncement.objects.create(
            title="Inactive announcement",
            message="Manually hidden.",
            published_at=now - timedelta(minutes=1),
            is_active=False,
            created_by=self.content_manager,
            updated_by=self.content_manager,
        )
        self.client.force_authenticate(self.active_member_user)

        response = self.client.get("/api/v1/content/member-announcements/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(current.id))

    def test_inactive_member_cannot_access_member_announcement_feed(self):
        self.client.force_authenticate(self.ordinary_user)

        response = self.client.get("/api/v1/content/member-announcements/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_content_manager_can_filter_search_and_update_announcements(self):
        now = timezone.now()
        scheduled = MemberAnnouncement.objects.create(
            title="Scheduled training",
            message="A training announcement for members.",
            published_at=now + timedelta(days=1),
            created_by=self.content_manager,
            updated_by=self.content_manager,
        )
        MemberAnnouncement.objects.create(
            title="Different topic",
            message="This item should not match the search.",
            published_at=now - timedelta(minutes=1),
            created_by=self.content_manager,
            updated_by=self.content_manager,
        )
        self.client.force_authenticate(self.content_manager)

        list_response = self.client.get(
            "/api/v1/content/announcements/",
            {"state": "scheduled", "search": "training"},
        )
        update_response = self.client.patch(
            f"/api/v1/content/announcements/{scheduled.id}/",
            {"is_active": False},
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(
            list_response.data["results"][0]["id"],
            str(scheduled.id),
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["state"], "inactive")
