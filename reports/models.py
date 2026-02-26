from django.db import models
from django.contrib.auth.models import User


def report_upload_path(instance, filename):
    return f"reports/user_{instance.user_id}/{filename}"


class MedicalReport(models.Model):
    """Stores an uploaded medical report and its AI-generated analysis."""

    FILE_TYPE_CHOICES = [
        ("pdf", "PDF"),
        ("csv", "CSV"),
        ("image", "Image"),
        ("unknown", "Unknown"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reports")
    file = models.FileField(upload_to=report_upload_path)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default="unknown")
    original_filename = models.CharField(max_length=255)

    # Extracted text and AI outputs
    extracted_text = models.TextField(blank=True, default="")
    summary = models.TextField(blank=True, default="")
    diet_advice = models.TextField(blank=True, default="")

    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Report({self.user.username}, {self.original_filename})"
