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

from ..models import (
    ContentCategory,
    ContentSection,
    GalleryItem,
    NewsArticle,
    PageSettings,
    PublicationStatus,
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
