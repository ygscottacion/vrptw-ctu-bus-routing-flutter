from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import deps
from app.models.profile import Profile
from app.models.wallet import Wallet
from app.services.wallet_service import create_wallet_for_new_account

router = APIRouter()


class WalletBalanceResponse(BaseModel):
    balance: int


@router.get("/me", response_model=WalletBalanceResponse)
def read_my_wallet(
    db: Session = Depends(deps.get_db),
    current_profile: Profile = Depends(deps.get_current_profile),
) -> WalletBalanceResponse:
    """Return the authenticated user's wallet balance."""
    wallet = db.query(Wallet).filter(Wallet.user_id == current_profile.id).one_or_none()
    if wallet is None:
        wallet = create_wallet_for_new_account(db, current_profile.id)
    if wallet is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not initialize wallet",
        )
    return WalletBalanceResponse(balance=wallet.balance)
