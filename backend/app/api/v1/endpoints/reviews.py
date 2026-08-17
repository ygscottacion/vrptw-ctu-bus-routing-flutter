from typing import Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User

router = APIRouter()

class ReviewCreate(BaseModel):
    route_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: int
    user_id: int
    route_id: int
    rating: int
    comment: Optional[str] = None
    created_at: str

_mock_reviews = []
_review_id_counter = 1

@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    review_in: ReviewCreate,
    current_student: User = Depends(deps.get_current_student)
) -> Any:
    global _review_id_counter
    review = {
        "id": _review_id_counter,
        "user_id": current_student.id,
        "route_id": review_in.route_id,
        "rating": review_in.rating,
        "comment": review_in.comment,
        "created_at": datetime.utcnow().isoformat()
    }
    _review_id_counter += 1
    _mock_reviews.append(review)
    return review

@router.get("/", response_model=List[ReviewResponse])
def read_reviews() -> Any:
    return _mock_reviews
