from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import deps
from app.models.profile import Profile
from app.schemas.profile import ProfileResponse, ProfileRoleUpdate

router = APIRouter()


@router.get("/", response_model=list[ProfileResponse])
def read_users(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_admin: Profile = Depends(deps.get_current_admin),
) -> Any:
    """List Supabase Auth accounts with their application profiles."""
    rows = db.execute(
        text(
            """
            SELECT
                auth_user.id,
                COALESCE(profile.role::text, 'passenger') AS role,
                COALESCE(profile.full_name, auth_user.raw_user_meta_data ->> 'full_name') AS full_name,
                COALESCE(profile.phone, auth_user.raw_user_meta_data ->> 'phone') AS phone,
                auth_user.email
            FROM auth.users AS auth_user
            LEFT JOIN public.profiles AS profile ON profile.id = auth_user.id
            ORDER BY auth_user.created_at, auth_user.id
            OFFSET :skip LIMIT :limit
            """
        ),
        {"skip": max(skip, 0), "limit": min(max(limit, 1), 500)},
    ).mappings()
    return [dict(row) for row in rows]


@router.put("/{user_id}/role", response_model=ProfileResponse)
def update_user_role(
    user_id: UUID,
    role_in: ProfileRoleUpdate,
    db: Session = Depends(deps.get_db),
    current_admin: Profile = Depends(deps.get_current_admin),
) -> Any:
    """Update a Supabase account's application role in public.profiles."""
    exists = db.execute(
        text("SELECT 1 FROM auth.users WHERE id = :user_id"),
        {"user_id": user_id},
    ).first()
    if not exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    profile = db.query(Profile).filter(Profile.id == user_id).one_or_none()
    if profile is None:
        profile = Profile(id=user_id, role=role_in.role)
        db.add(profile)
    else:
        profile.role = role_in.role

    db.commit()
    db.refresh(profile)

    if profile.role.value == "passenger":
        from app.services.wallet_service import create_wallet_for_new_account

        create_wallet_for_new_account(db, profile.id)

    auth_row = db.execute(
        text("SELECT email FROM auth.users WHERE id = :user_id"),
        {"user_id": user_id},
    ).mappings().one()
    return {
        "id": profile.id,
        "role": profile.role,
        "full_name": profile.full_name,
        "phone": profile.phone,
        "email": auth_row["email"],
    }
