from django.urls import path
from . import views

urlpatterns = [
    path("", views.list_reports, name="list_reports"),
    path("upload/", views.upload_report, name="upload_report"),
    path("<int:pk>/", views.report_detail, name="report_detail"),
]
