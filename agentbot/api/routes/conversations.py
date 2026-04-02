"""Conversation and chat routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from agentbot.api.schemas import (
    ConversationRunsDetail,
    ConversationDetail,
    ConversationSummary,
    CreateConversationRequest,
    MessagePayload,
    RenameConversationRequest,
    RunSummary,
    SendRunResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from agentbot.api.serializers import (
    serialize_run,
    serialize_messages,
    serialize_sqlite_conversation,
    serialize_transcript_messages,
)
from agentbot.services.chat import ChatService
from agentbot.services.conversations import ConversationService
from agentbot.storage.db import AgentDatabase
from agentbot.storage.repositories import RunRepository

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _conversation_service() -> ConversationService:
    return ConversationService()


def _chat_service() -> ChatService:
    return ChatService()


@router.get("", response_model=list[ConversationSummary])
def list_conversations():
    service = _conversation_service()
    return [serialize_sqlite_conversation(meta) for meta in service.list_conversations()]


@router.post("", response_model=ConversationSummary, status_code=status.HTTP_201_CREATED)
def create_conversation(request: CreateConversationRequest):
    service = _conversation_service()
    meta = service.create_conversation(request.name)
    return serialize_sqlite_conversation(meta)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str):
    service = _conversation_service()
    try:
        meta, messages = service.get_conversation(conversation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "conversation": serialize_sqlite_conversation(meta),
        "messages": serialize_transcript_messages(messages),
    }


@router.get("/{conversation_id}/messages", response_model=list[MessagePayload])
def get_conversation_messages(conversation_id: str):
    service = _conversation_service()
    try:
        _meta, messages = service.get_conversation(conversation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return serialize_transcript_messages(messages)


@router.get("/{conversation_id}/runs", response_model=ConversationRunsDetail)
def list_conversation_runs(conversation_id: str):
    service = _conversation_service()
    try:
        meta, _messages = service.get_conversation(conversation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    database = AgentDatabase()
    database.initialize()
    with database.connect() as connection:
        runs = RunRepository(connection).list_for_conversation(conversation_id)

    return {
        "conversation": serialize_sqlite_conversation(meta),
        "runs": [serialize_run(run) for run in runs],
    }


@router.patch("/{conversation_id}", response_model=ConversationSummary)
def rename_conversation(conversation_id: str, request: RenameConversationRequest):
    service = _conversation_service()
    try:
        meta = service.rename_conversation(conversation_id, request.name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return serialize_sqlite_conversation(meta)


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
        (message for message in reversed(serialize_transcript_messages(messages)) if message["role"] == "assistant"),
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
        "conversation": serialize_sqlite_conversation(meta),
        "messages": serialize_transcript_messages(messages),
        "reply": reply_payload,
    }


@router.post("/{conversation_id}/runs", response_model=SendRunResponse)
def send_run_to_conversation(conversation_id: str, request: SendMessageRequest):
    chat_service = _chat_service()
    try:
        meta, run, messages, reply = chat_service.send_run_to_conversation(
            conversation_id,
            request.content,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    reply_payload = next(
        (message for message in reversed(serialize_transcript_messages(messages)) if message["role"] == "assistant"),
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
        "conversation": serialize_sqlite_conversation(meta),
        "run": serialize_run(run),
        "messages": serialize_transcript_messages(messages),
        "reply": reply_payload,
    }


def _run_stream_response(conversation_id: str, request: SendMessageRequest):
    chat_service = _chat_service()

    def event_stream():
        try:
            for event in chat_service.stream_message_to_conversation(conversation_id, request.content):
                payload = json.dumps(event.get("data", {}), ensure_ascii=False)
                yield f"event: {event['event']}\n".encode("utf-8")
                yield f"data: {payload}\n\n".encode("utf-8")
        except FileNotFoundError as exc:
            payload = json.dumps({"message": str(exc)}, ensure_ascii=False)
            yield b"event: error\n"
            yield f"data: {payload}\n\n".encode("utf-8")
            yield b"event: done\n"
            yield b"data: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{conversation_id}/runs/stream")
def stream_run_for_conversation(conversation_id: str, request: SendMessageRequest):
    return _run_stream_response(conversation_id, request)


@router.post("/{conversation_id}/messages/stream")
def stream_message_to_conversation(conversation_id: str, request: SendMessageRequest):
    # Compatibility alias during the API cutover. New clients should use /runs/stream.
    return _run_stream_response(conversation_id, request)
