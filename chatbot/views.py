import sys
import os

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Conversation, Message
from .serializers import ConversationSerializer, ConversationListSerializer

# Allow ai_engine to be imported regardless of where manage.py is run from
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai_engine"))
from ai_engine import generate_chat_response  # noqa: E402


# ---------------------------------------------------------------------------
# Conversation management
# ---------------------------------------------------------------------------

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def conversations(request):
    """List all conversations for the authenticated user, or start a new one."""
    if request.method == "GET":
        convs = Conversation.objects.filter(user=request.user)
        return Response(ConversationListSerializer(convs, many=True).data)

    # POST – create new conversation
    conv = Conversation.objects.create(user=request.user)
    return Response(ConversationSerializer(conv).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def conversation_detail(request, pk):
    """Retrieve or delete a specific conversation (with full message history)."""
    try:
        conv = Conversation.objects.get(pk=pk, user=request.user)
    except Conversation.DoesNotExist:
        return Response({"error": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        conv.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    return Response(ConversationSerializer(conv).data)


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat(request):
    """
    POST /api/chat/message/
    Body: { "message": "...", "conversation_id": <optional int> }
    Returns: { "response": "...", "is_emergency": bool, "diseases": [...], "conversation_id": int }
    """
    user_message = request.data.get("message", "").strip()
    if not user_message:
        return Response({"error": "Message cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

    # Get or create conversation
    conv_id = request.data.get("conversation_id")
    if conv_id:
        try:
            conv = Conversation.objects.get(pk=conv_id, user=request.user)
        except Conversation.DoesNotExist:
            return Response({"error": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
    else:
        # Auto-create a conversation with title from the first message
        title = user_message[:80]
        conv = Conversation.objects.create(user=request.user, title=title)

    # Save user message
    Message.objects.create(conversation=conv, role="user", content=user_message)

    # Generate AI response
    result = generate_chat_response(user_message)

    # Save bot response
    bot_msg = Message.objects.create(
        conversation=conv,
        role="bot",
        content=result["response"],
        is_emergency=result["is_emergency"],
        diseases_detected=result["diseases"],
    )

    # Update conversation title if still empty
    if not conv.title:
        conv.title = user_message[:80]
        conv.save(update_fields=["title", "updated_at"])

    return Response(
        {
            "response": result["response"],
            "is_emergency": result["is_emergency"],
            "diseases": result["diseases"],
            "conversation_id": conv.id,
            "message_id": bot_msg.id,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def history(request, conv_id):
    """Return all messages in a conversation."""
    try:
        conv = Conversation.objects.get(pk=conv_id, user=request.user)
    except Conversation.DoesNotExist:
        return Response({"error": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)

    return Response(ConversationSerializer(conv).data)
