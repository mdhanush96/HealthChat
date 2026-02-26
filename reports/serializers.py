from rest_framework import serializers
from .models import MedicalReport


class MedicalReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalReport
        fields = (
            "id",
            "original_filename",
            "file_type",
            "extracted_text",
            "summary",
            "diet_advice",
            "uploaded_at",
            "processed",
        )
        read_only_fields = fields


class ReportUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalReport
        fields = ("file",)
