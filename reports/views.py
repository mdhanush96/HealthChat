import logging
import os
import sys

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import MedicalReport
from .serializers import MedicalReportSerializer
from .report_processor import detect_file_type, extract_text, generate_diet_advice_from_text

# Allow ai_engine to be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai_engine"))
from ai_engine import summarise_text  # noqa: E402

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "\n\n---\n"
    "⚠️ **Medical Disclaimer**: This report analysis is for informational purposes only "
    "and does NOT constitute a medical diagnosis. Please consult your doctor to interpret "
    "your medical report results."
)

ALLOWED_EXTENSIONS = {".pdf", ".csv", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".webp"}
MAX_UPLOAD_SIZE_MB = 10


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_report(request):
    """
    POST /api/reports/upload/
    Accepts a multipart/form-data upload with key 'file'.
    Processes the file, extracts text, generates a T5 summary and diet advice.
    """
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

    # Validate extension
    ext = os.path.splitext(uploaded_file.name)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return Response(
            {"error": f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate size
    if uploaded_file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        return Response(
            {"error": f"File too large. Maximum allowed size is {MAX_UPLOAD_SIZE_MB} MB."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    file_type = detect_file_type(uploaded_file.name)

    # Create DB record and save file
    report = MedicalReport.objects.create(
        user=request.user,
        file=uploaded_file,
        file_type=file_type,
        original_filename=uploaded_file.name,
    )

    # Extract text
    extracted = extract_text(report.file.path, file_type)
    report.extracted_text = extracted

    # Summarise with T5 if we have content
    if extracted.strip():
        try:
            report.summary = summarise_text(extracted) + DISCLAIMER
        except Exception as exc:
            logger.error("T5 summarisation failed for report %s: %s", report.id, exc)
            report.summary = (
                extracted[:500] + "...\n\n*(Full text truncated – summarisation unavailable)*"
                + DISCLAIMER
            )

        # Diet advice (rule-based)
        report.diet_advice = generate_diet_advice_from_text(extracted)
    else:
        report.summary = "Could not extract text from the uploaded file." + DISCLAIMER
        report.diet_advice = ""

    report.processed = True
    report.save()

    return Response(MedicalReportSerializer(report).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_reports(request):
    """GET /api/reports/ – List all reports for the authenticated user."""
    reports = MedicalReport.objects.filter(user=request.user)
    return Response(MedicalReportSerializer(reports, many=True).data)


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def report_detail(request, pk):
    """GET or DELETE a specific report."""
    try:
        report = MedicalReport.objects.get(pk=pk, user=request.user)
    except MedicalReport.DoesNotExist:
        return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        # Remove file from disk
        if report.file and os.path.isfile(report.file.path):
            os.remove(report.file.path)
        report.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    return Response(MedicalReportSerializer(report).data)
