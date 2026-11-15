from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Department, Position


class OrganizationApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.active_department = Department.objects.create(
            name="Technology",
            description="Technology department",
        )
        cls.active_position = Position.objects.create(
            department=cls.active_department,
            name="Developer",
        )
        cls.inactive_position = Position.objects.create(
            department=cls.active_department,
            name="Retired position",
            is_active=False,
        )
        cls.inactive_department = Department.objects.create(
            name="Retired department",
            is_active=False,
        )

    def test_public_list_returns_only_active_reference_data(self):
        response = self.client.get("/api/v1/organization/departments/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Technology")
        self.assertEqual(len(response.data[0]["positions"]), 1)
        self.assertEqual(response.data[0]["positions"][0]["name"], "Developer")

    def test_public_detail_returns_active_department(self):
        response = self.client.get(
            f"/api/v1/organization/departments/{self.active_department.id}/"
        )
        inactive_response = self.client.get(
            f"/api/v1/organization/departments/{self.inactive_department.id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(inactive_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_schema_documents_organization_reference_routes(self):
        response = self.client.get(
            "/api/schema/",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            "/api/v1/organization/departments/",
            response.data["paths"],
        )
