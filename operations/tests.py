import os
import pandas as pd
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from operations.models import ContributionRecord

CustomUser = get_user_model()

class BulkUploadTests(TestCase):
    def setUp(self):
        """Setup test users and test client"""
        self.client = Client()
        self.user = CustomUser.objects.create(email="test@nitda.gov.ng", nitda_id="12345")
        self.file_path = "test_contributions.xlsx"

        # Create a test Excel file
        data = {
            "Email": ["test@example.com"],
            "Amount": [1000],
            "Month": ["January"],
            "Year": [2025]
        }
        df = pd.DataFrame(data)
        df.to_excel(self.file_path, index=False)

    def test_bulk_upload_view(self):
        """Test bulk upload file processing"""
        with open(self.file_path, "rb") as f:
            file = SimpleUploadedFile(self.file_path, f.read(), content_type="application/vnd.ms-excel")
            response = self.client.post("/upload/", {"file": file}, format="multipart")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Preview Contributions")

    def test_confirm_bulk_upload_view(self):
        """Test confirming contributions"""
        self.client.session["contributions_preview"] = [
            {"Email": "test@example.com", "Amount": 1000, "Month": "January", "Year": 2025}
        ]
        self.client.session.save()

        response = self.client.post("/confirm/")
        self.assertEqual(response.status_code, 302)  # Redirect expected
        self.assertTrue(ContributionRecord.objects.filter(employee=self.user).exists())

    def tearDown(self):
        """Cleanup test file"""
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
