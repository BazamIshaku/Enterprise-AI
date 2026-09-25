"""Authentication and tenant-bound request dependencies."""
from typing import Annotated
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session
from .models import Membership, User, Workspace
from .security import JWT_ALGORITHM, JWT_SECRET

bearer_scheme = HTTPBearer()
SessionDependency = Annotated[Session, Depends(get_session)]


def get_current_user(credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)], session: SessionDependency) -> User:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
    except jwt.PyJWTError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token") from error
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_workspace(x_workspace_id: Annotated[str, Header()], user: Annotated[User, Depends(get_current_user)], session: SessionDependency) -> Workspace:
    workspace = session.get(Workspace, x_workspace_id)
    membership = session.scalar(select(Membership).where(Membership.user_id == user.id, Membership.workspace_id == x_workspace_id))
    if workspace is None or membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this workspace")
    return workspace


def get_admin_workspace(x_workspace_id: Annotated[str, Header()], user: Annotated[User, Depends(get_current_user)], session: SessionDependency) -> Workspace:
    workspace = session.get(Workspace, x_workspace_id)
    membership = session.scalar(select(Membership).where(Membership.user_id == user.id, Membership.workspace_id == x_workspace_id))
    if workspace is None or membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this workspace")
    if membership.role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access is required")
    return workspace
