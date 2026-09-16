"""Version-one HTTP routes."""
import json
import re
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session
from .dependencies import get_current_user, get_workspace
from .models import Assistant, Conversation, Membership, Message, User, Workspace
from .nia import stream_reply
from .schemas import AssistantCreate, AssistantResponse, ConversationCreate, ConversationResponse, LoginRequest, MessageCreate, MessageResponse, PasswordResetRequest, RegisterRequest, TokenResponse, UserResponse, WorkspaceResponse
from .security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1")
SessionDependency = Annotated[Session, Depends(get_session)]


def workspace_slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60] or "workspace"
    return base


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, session: SessionDependency) -> TokenResponse:
    if session.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    slug = workspace_slug(payload.workspace_name)
    if session.scalar(select(Workspace).where(Workspace.slug == slug)):
        raise HTTPException(status_code=409, detail="Choose a different workspace name")
    user = User(email=payload.email.lower(), full_name=payload.full_name, password_hash=hash_password(payload.password))
    workspace = Workspace(name=payload.workspace_name, slug=slug)
    session.add_all([user, workspace])
    session.flush()
    session.add(Membership(user_id=user.id, workspace_id=workspace.id, role="owner"))
    session.commit()
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: SessionDependency) -> TokenResponse:
    user = session.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/auth/me", response_model=UserResponse)
def current_account(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user


@router.post("/auth/password-reset", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(_: PasswordResetRequest) -> dict[str, str]:
    # This response deliberately does not reveal whether an address is registered.
    # The email-delivery provider will be connected in the production integration.
    return {"message": "If an account exists, reset instructions will be sent shortly."}


@router.get("/workspaces", response_model=list[WorkspaceResponse])
def list_workspaces(user: Annotated[User, Depends(get_current_user)], session: SessionDependency) -> list[Workspace]:
    return list(session.scalars(select(Workspace).join(Membership).where(Membership.user_id == user.id).order_by(Workspace.name)))


@router.get("/assistants", response_model=list[AssistantResponse])
def list_assistants(workspace: Annotated[Workspace, Depends(get_workspace)], session: SessionDependency) -> list[Assistant]:
    return list(session.scalars(select(Assistant).where(Assistant.workspace_id == workspace.id).order_by(Assistant.created_at.desc())))


@router.post("/assistants", response_model=AssistantResponse, status_code=status.HTTP_201_CREATED)
def create_assistant(payload: AssistantCreate, workspace: Annotated[Workspace, Depends(get_workspace)], session: SessionDependency) -> Assistant:
    assistant = Assistant(workspace_id=workspace.id, **payload.model_dump())
    session.add(assistant)
    session.commit()
    session.refresh(assistant)
    return assistant


@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(workspace: Annotated[Workspace, Depends(get_workspace)], session: SessionDependency) -> list[Conversation]:
    return list(session.scalars(select(Conversation).where(Conversation.workspace_id == workspace.id).order_by(Conversation.updated_at.desc())))


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(payload: ConversationCreate, workspace: Annotated[Workspace, Depends(get_workspace)], session: SessionDependency) -> Conversation:
    conversation = Conversation(workspace_id=workspace.id, title=payload.title)
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
def list_messages(conversation_id: str, workspace: Annotated[Workspace, Depends(get_workspace)], session: SessionDependency) -> list[Message]:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None or conversation.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return list(session.scalars(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)))


@router.post("/conversations/{conversation_id}/messages/stream")
async def send_message(conversation_id: str, payload: MessageCreate, workspace: Annotated[Workspace, Depends(get_workspace)], session: SessionDependency) -> StreamingResponse:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None or conversation.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    session.add(Message(conversation_id=conversation.id, role="user", content=payload.content))
    if conversation.title == "New conversation":
        conversation.title = payload.content[:157] + ("..." if len(payload.content) > 157 else "")
    session.commit()
    history = list(session.scalars(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)))

    async def event_stream():
        response_text = ""
        try:
            async for chunk in stream_reply([{"role": message.role, "content": message.content} for message in history]):
                response_text += chunk
                yield f"data: {json.dumps({'delta': chunk})}\n\n"
            session.add(Message(conversation_id=conversation.id, role="assistant", content=response_text))
            session.commit()
            yield "data: [DONE]\n\n"
        except RuntimeError as error:
            yield f"data: {json.dumps({'error': str(error)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

