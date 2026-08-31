from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api import deps
from app.core import security
from app.crud import crud_user
from app.models.profile import Profile
from app.schemas.profile import ProfileResponse
from app.schemas.user import UserCreate, UserResponse, Token, LoginRequest

router = APIRouter()


@router.get("/me", response_model=ProfileResponse)
def read_user_me(
    current_profile: Profile = Depends(deps.get_current_profile),
) -> Any:
    """
    Get current authenticated profile using Supabase Auth JWT.
    """
    return current_profile


@router.post("/login", response_model=Token, deprecated=True)
def login_access_token(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    DEPRECATED: Legacy internal OAuth2 login.
    Flutter app should authenticate directly with Supabase Auth SDK.
    """
    user = crud_user.authenticate_user(
        db, username=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
        )
    access_token = security.create_access_token(subject=user.username)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login/json", response_model=Token, deprecated=True)
def login_json(
    login_data: LoginRequest, db: Session = Depends(deps.get_db)
) -> Any:
    """
    DEPRECATED: Legacy JSON login.
    Flutter app should authenticate directly with Supabase Auth SDK.
    """
    user = crud_user.authenticate_user(
        db, username=login_data.username, password=login_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
        )
    access_token = security.create_access_token(subject=user.username)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserResponse, deprecated=True)
def register_user(
    user_in: UserCreate, db: Session = Depends(deps.get_db)
) -> Any:
    """
    DEPRECATED: Legacy user registration.
    Flutter app should register users directly with Supabase Auth SDK.
    """
    user = crud_user.get_user_by_username(db, username=user_in.username)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    return crud_user.create_user(db, user_in=user_in)
