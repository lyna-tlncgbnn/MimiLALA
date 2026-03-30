"""Conversation and chat routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from agentbot.api.schemas import (
    ConversationDetail,
    ConversationSummary,
    CreateConversationRequest,
    MessagePayload,
    RenameConversationRequest,
    SendMessageRequest,
    SendMessageResponse,
)
from agentbot.api.serializers import serialize_conversation_meta, serialize_messages
from agentbot.services.chat import ChatService
from agentbot.services.conversations import ConversationService

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _conversation_service() -> ConversationService:
    return ConversationService()


def _chat_service() -> ChatService:
    return ChatService()


@router.get("", response_model=list[ConversationSummary])
def list_conversations():
    service = _conversation_service()
    return [serialize_conversation_meta(meta) for meta in service.list_conversations()]


@router.post("", response_model=ConversationSummary, status_code=status.HTTP_201_CREATED)
def create_conversation(request: CreateConversationRequest):
    service = _conversation_service()
    meta = service.create_conversation(request.name)
    return serialize_conversation_meta(meta)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str):
    service = _conversation_service()
    try:
        meta, messages = service.get_conversation(conversation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "conversation": serialize_conversation_meta(meta),
        "messages": serialize_messages(messages),
    }


@router.get("/{conversation_id}/messages", response_model=list[MessagePayload])
def get_conversation_messages(conversation_id: str):
    service = _conversation_service()
    try:
        _meta, messages = service.get_conversation(conversation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return serialize_messages(messages)


@router.patch("/{conversation_id}", response_model=ConversationSummary)
def rename_conversation(conversation_id: str, request: RenameConversationRequest):
    service = _conversation_service()
    try:
        meta = service.rename_conversation(conversation_id, request.name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return serialize_conversation_meta(meta)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: str):
    service = _conversation_service()
    try:
        service.delete_conversation(conversation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return None


@router.post("/{conversation_id}/messages", response_model=SendMessageResponse)
def send_message_to_conversation(conversation_id: str, request: SendMessageRequest):
    chat_service = _chat_service()
    try:
        meta, messages, reply = chat_service.send_message_to_conversation(
            conversation_id,
            request.content,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    reply_payload = next(
        (message for message in reversed(serialize_messages(messages)) if message["role"] == "assistant"),
        {
            "message_id": None,
            "timestamp": None,
            "role": "assistant",
            "content": reply,
            "name": None,
            "tool_call_id": None,
            "tool_calls": None,
        },
    )
    return {
        "conversation": serialize_conversation_meta(meta),
        "messages": serialize_messages(messages),
        "reply": reply_payload,
    }
