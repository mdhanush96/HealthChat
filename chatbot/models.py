from django.db import models
from django.contrib.auth.models import User


class Conversation(models.Model):
    """Stores a single chat session per user."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations")
    title = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Conversation({self.user.username}, {self.created_at:%Y-%m-%d})"


class Message(models.Model):
    """Stores an individual message (user or bot) within a conversation."""

    ROLE_CHOICES = [("user", "User"), ("bot", "Bot")]

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    is_emergency = models.BooleanField(default=False)
    diseases_detected = models.JSONField(default=list, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"Message({self.role}, conv={self.conversation_id})"
