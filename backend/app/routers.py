"""Version-one HTTP routes."""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
from uuid import uuid4
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session
from .catalog import DEPARTMENTS, DEPARTMENT_BY_ID, ROLE_BY_ID, ROLE_TEMPLATES
from .dependencies import get_admin_workspace, get_current_user, get_workspace
from .models import Assistant, Conversation, KnowledgeDocument, Membership, Message, TaskMessage, User, Workspace, WorkTask
from .knowledge_processing import process_knowledge_document
from .task_processing import process_work_task
from .nia import stream_reply
from .schemas import AssistantCreate, AssistantResponse, AssistantUpdate, CatalogDepartment, CatalogRole, ConversationCreate, ConversationResponse, KnowledgeDocumentResponse, LoginRequest, MemberAdd, MemberResponse, MessageCreate, MessageResponse, PasswordResetRequest, RegisterRequest, TaskMessageCreate, TaskMessageResponse, TokenResponse, UserResponse, WorkspaceResponse, WorkTaskCreate, WorkTaskResponse
from .security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1")
SessionDependency = Annotated[Session, Depends(get_session)]
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./private_uploads"))
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_UPLOADS = {
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain"},
    ".csv": {"text/csv", "application/vnd.ms-excel"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".webp": {"image/webp"},
}


def content_matches_extension(suffix: str, sample: bytes) -> bool:
    if suffix == ".pdf":
        return sample.startswith(b"%PDF-")
    if suffix == ".docx":
        return sample.startswith(b"PK\x03\x04")
    if suffix == ".png":
        return sample.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix in {".jpg", ".jpeg"}:
        return sample.startswith(b"\xff\xd8\xff")
    if suffix == ".webp":
        return len(sample) >= 12 and sample.startswith(b"RIFF") and sample[8:12] == b"WEBP"
    return b"\x00" not in sample


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


@router.get("/members", response_model=list[MemberResponse])
def list_members(workspace: Annotated[Workspace, Depends(get_workspace)], session: SessionDependency) -> list[dict]:
    rows = session.execute(select(Membership, User).join(User, User.id == Membership.user_id).where(Membership.workspace_id == workspace.id).order_by(User.full_name)).all()
    return [{"id": membership.id, "user_id": user.id, "email": user.email, "full_name": user.full_name, "role": membership.role, "created_at": membership.created_at} for membership, user in rows]


@router.post("/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def add_member(payload: MemberAdd, workspace: Annotated[Workspace, Depends(get_admin_workspace)], session: SessionDependency) -> dict:
    user = session.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None:
        raise HTTPException(status_code=404, detail="Ask this employee to create an EUNIA account first, then add their email here")
    if session.scalar(select(Membership).where(Membership.workspace_id == workspace.id, Membership.user_id == user.id)):
        raise HTTPException(status_code=409, detail="This employee already belongs to the workspace")
    membership = Membership(workspace_id=workspace.id, user_id=user.id, role=payload.role)
    session.add(membership)
    session.commit()
    session.refresh(membership)
    return {"id": membership.id, "user_id": user.id, "email": user.email, "full_name": user.full_name, "role": membership.role, "created_at": membership.created_at}


@router.get("/catalog/departments", response_model=list[CatalogDepartment])
def list_departments(_: Annotated[User, Depends(get_current_user)]) -> list[dict]:
    return DEPARTMENTS


@router.get("/catalog/roles", response_model=list[CatalogRole])
def list_roles(_: Annotated[User, Depends(get_current_user)]) -> list[dict]:
    return ROLE_TEMPLATES


@router.get("/assistants", response_model=list[AssistantResponse])
def list_assistants(workspace: Annotated[Workspace, Depends(get_workspace)], session: SessionDependency) -> list[Assistant]:
    return list(session.scalars(select(Assistant).where(Assistant.workspace_id == workspace.id).order_by(Assistant.created_at.desc())))


@router.post("/assistants", response_model=AssistantResponse, status_code=status.HTTP_201_CREATED)
def create_assistant(payload: AssistantCreate, workspace: Annotated[Workspace, Depends(get_admin_workspace)], session: SessionDependency) -> Assistant:
    department = DEPARTMENT_BY_ID.get(payload.department)
    role = ROLE_BY_ID.get(payload.role_template_id)
    if department is None:
        raise HTTPException(status_code=422, detail="Choose a valid department")
    if role is None or role["department_id"] != payload.department:
        raise HTTPException(status_code=422, detail="Choose a role that belongs to this department")
    values = payload.model_dump()
    values["department"] = department["name"]
    values["role"] = role["name"]
    if not values["capabilities"]:
        values["capabilities"] = role["capabilities"]
    assistant = Assistant(workspace_id=workspace.id, **values)
    session.add(assistant)
    session.commit()
    session.refresh(assistant)
    return assistant


def assistant_for_workspace(assistant_id: str, workspace: Workspace, session: Session) -> Assistant:
    assistant = session.get(Assistant, assistant_id)
    if assistant is None or assistant.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="AI employee not found")
    return assistant


@router.patch("/assistants/{assistant_id}", response_model=AssistantResponse)
def update_assistant(assistant_id: str, payload: AssistantUpdate, workspace: Annotated[Workspace, Depends(get_admin_workspace)], session: SessionDependency) -> Assistant:
    assistant = assistant_for_workspace(assistant_id, workspace, session)
    department = DEPARTMENT_BY_ID.get(payload.department)
    role = ROLE_BY_ID.get(payload.role_template_id)
    if department is None:
        raise HTTPException(status_code=422, detail="Choose a valid department")
    if role is None or role["department_id"] != payload.department:
        raise HTTPException(status_code=422, detail="Choose a role that belongs to this department")
    assistant.name = payload.name
    assistant.department = department["name"]
    assistant.role_template_id = role["id"]
    assistant.role = role["name"]
    assistant.capabilities = role["capabilities"]
    assistant.status = payload.status
    assistant.access_level = payload.access_level
    assistant.instructions = payload.instructions
    session.commit()
    session.refresh(assistant)
    return assistant


@router.get("/assistants/{assistant_id}/knowledge", response_model=list[KnowledgeDocumentResponse])
def list_knowledge_documents(assistant_id: str, workspace: Annotated[Workspace, Depends(get_workspace)], session: SessionDependency) -> list[KnowledgeDocument]:
    assistant_for_workspace(assistant_id, workspace, session)
    return list(session.scalars(select(KnowledgeDocument).where(KnowledgeDocument.assistant_id == assistant_id, KnowledgeDocument.workspace_id == workspace.id).order_by(KnowledgeDocument.created_at.desc())))


@router.post("/assistants/{assistant_id}/knowledge", response_model=KnowledgeDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_knowledge_document(assistant_id: str, background_tasks: BackgroundTasks, file: Annotated[UploadFile, File()], workspace: Annotated[Workspace, Depends(get_admin_workspace)], user: Annotated[User, Depends(get_current_user)], session: SessionDependency) -> KnowledgeDocument:
    assistant_for_workspace(assistant_id, workspace, session)
    original_name = Path(file.filename or "").name
    suffix = Path(original_name).suffix.lower()
    if not original_name or len(original_name) > 255 or suffix not in ALLOWED_UPLOADS:
        raise HTTPException(status_code=415, detail="Use PDF, DOCX, TXT, CSV, PNG, JPG, or WEBP files")
    if file.content_type not in ALLOWED_UPLOADS[suffix]:
        raise HTTPException(status_code=415, detail="The file type does not match its extension")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    storage_key = f"{workspace.id}/{assistant_id}/{uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / storage_key
    destination.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    sample = b""
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                if not sample:
                    sample = chunk[:32]
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Files must be 10 MB or smaller")
                output.write(chunk)
        if size == 0:
            raise HTTPException(status_code=422, detail="The uploaded file is empty")
        if not content_matches_extension(suffix, sample):
            raise HTTPException(status_code=415, detail="The file content does not match its extension")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    document = KnowledgeDocument(workspace_id=workspace.id, assistant_id=assistant_id, uploaded_by=user.id, file_name=original_name, storage_key=storage_key, content_type=file.content_type, size_bytes=size, status="queued")
    session.add(document)
    session.commit()
    session.refresh(document)
    background_tasks.add_task(process_knowledge_document, document.id)
    return document


@router.post("/assistants/{assistant_id}/knowledge/{document_id}/retry", response_model=KnowledgeDocumentResponse)
def retry_knowledge_document(assistant_id: str, document_id: str, background_tasks: BackgroundTasks, workspace: Annotated[Workspace, Depends(get_admin_workspace)], session: SessionDependency) -> KnowledgeDocument:
    assistant_for_workspace(assistant_id, workspace, session)
    document = session.get(KnowledgeDocument, document_id)
    if document is None or document.assistant_id != assistant_id or document.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Training file not found")
    if document.status == "processing":
        raise HTTPException(status_code=409, detail="This training file is already being processed")
    document.status = "queued"
    document.stage = "Waiting securely in the training queue"
    document.progress = 5
    document.feedback = "Training has been queued again. Progress will update automatically."
    session.commit()
    session.refresh(document)
    background_tasks.add_task(process_knowledge_document, document.id)
    return document


def task_for_workspace(task_id: str, workspace: Workspace, session: Session) -> WorkTask:
    task = session.get(WorkTask, task_id)
    if task is None or task.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/work/tasks", response_model=list[WorkTaskResponse])
def list_work_tasks(workspace: Annotated[Workspace, Depends(get_workspace)], session: SessionDependency) -> list[WorkTask]:
    return list(session.scalars(select(WorkTask).where(WorkTask.workspace_id == workspace.id).order_by(WorkTask.created_at.desc())))


@router.post("/work/tasks", response_model=WorkTaskResponse, status_code=status.HTTP_201_CREATED)
def create_work_task(payload: WorkTaskCreate, background_tasks: BackgroundTasks, workspace: Annotated[Workspace, Depends(get_workspace)], user: Annotated[User, Depends(get_current_user)], session: SessionDependency) -> WorkTask:
    assistant = assistant_for_workspace(payload.assistant_id, workspace, session)
    if assistant.status != "active":
        raise HTTPException(status_code=409, detail="Activate and train this AI employee before assigning work")
    task = WorkTask(workspace_id=workspace.id, created_by=user.id, supervisor_id=user.id, **payload.model_dump())
    session.add(task)
    session.flush()
    session.add(TaskMessage(task_id=task.id, workspace_id=workspace.id, author_type="user", author_user_id=user.id, author_name=user.full_name, kind="assignment", content=payload.instructions))
    session.add(TaskMessage(task_id=task.id, workspace_id=workspace.id, author_type="assistant", author_name=assistant.name, kind="status", content=f"I have received ‘{payload.title}’. I’ll review the brief and approved company knowledge, then return the result for supervisor review."))
    session.commit()
    session.refresh(task)
    background_tasks.add_task(process_work_task, task.id)
    return task


@router.get("/work/tasks/{task_id}/messages", response_model=list[TaskMessageResponse])
def list_task_messages(task_id: str, workspace: Annotated[Workspace, Depends(get_workspace)], session: SessionDependency) -> list[TaskMessage]:
    task_for_workspace(task_id, workspace, session)
    return list(session.scalars(select(TaskMessage).where(TaskMessage.task_id == task_id, TaskMessage.workspace_id == workspace.id).order_by(TaskMessage.created_at)))


@router.post("/work/tasks/{task_id}/messages", response_model=TaskMessageResponse, status_code=status.HTTP_201_CREATED)
def add_task_message(task_id: str, payload: TaskMessageCreate, workspace: Annotated[Workspace, Depends(get_workspace)], user: Annotated[User, Depends(get_current_user)], session: SessionDependency) -> TaskMessage:
    task_for_workspace(task_id, workspace, session)
    message = TaskMessage(task_id=task_id, workspace_id=workspace.id, author_type="user", author_user_id=user.id, author_name=user.full_name, content=payload.content)
    session.add(message)
    session.commit()
    session.refresh(message)
    return message


@router.post("/work/tasks/{task_id}/approve", response_model=WorkTaskResponse)
def approve_work_task(task_id: str, workspace: Annotated[Workspace, Depends(get_workspace)], user: Annotated[User, Depends(get_current_user)], session: SessionDependency) -> WorkTask:
    task = task_for_workspace(task_id, workspace, session)
    membership = session.scalar(select(Membership).where(Membership.workspace_id == workspace.id, Membership.user_id == user.id))
    if task.supervisor_id != user.id and membership and membership.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Only the assigned supervisor or an administrator can approve this result")
    if task.status != "awaiting_review":
        raise HTTPException(status_code=409, detail="This task is not awaiting review")
    task.status = "completed"
    task.stage = "Approved and complete"
    task.progress = 100
    task.completed_at = datetime.now(timezone.utc)
    session.add(TaskMessage(task_id=task.id, workspace_id=workspace.id, author_type="user", author_user_id=user.id, author_name=user.full_name, kind="approval", content="Result reviewed and approved. The task is complete."))
    session.commit()
    session.refresh(task)
    return task


@router.post("/work/tasks/{task_id}/retry", response_model=WorkTaskResponse)
def retry_work_task(task_id: str, background_tasks: BackgroundTasks, workspace: Annotated[Workspace, Depends(get_workspace)], user: Annotated[User, Depends(get_current_user)], session: SessionDependency) -> WorkTask:
    task = task_for_workspace(task_id, workspace, session)
    if task.status != "failed":
        raise HTTPException(status_code=409, detail="Only failed tasks can be retried")
    task.status = "queued"
    task.stage = "Waiting for the AI employee"
    task.progress = 5
    session.add(TaskMessage(task_id=task.id, workspace_id=workspace.id, author_type="user", author_user_id=user.id, author_name=user.full_name, kind="status", content="Requested another attempt."))
    session.commit()
    session.refresh(task)
    background_tasks.add_task(process_work_task, task.id)
    return task


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

