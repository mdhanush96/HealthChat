from django.urls import path
from . import views

urlpatterns = [
    path("conversations/", views.conversations, name="conversations"),
    path("conversations/<int:pk>/", views.conversation_detail, name="conversation_detail"),
    path("message/", views.chat, name="chat"),
    path("history/<int:conv_id>/", views.history, name="history"),
]
