import enum
import datetime
import uuid
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class TransactionType(str, enum.Enum):
    PURCHASE = "purchase"
    REFUND = "refund"


class Wallet(Base):
    __tablename__ = "wallets"

    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    balance = Column(Integer, default=200000, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    profile = relationship("Profile", backref="wallet")
    transactions = relationship("WalletTransaction", back_populates="wallet", cascade="all, delete-orphan")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.user_id", ondelete="CASCADE"), nullable=False, index=True)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True, index=True)
    type = Column(
        SQLEnum(
            TransactionType,
            name="transaction_type",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    amount = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    wallet = relationship("Wallet", back_populates="transactions")
    ticket = relationship("Ticket")

    __table_args__ = (
        UniqueConstraint("ticket_id", "type", name="uq_wallet_transactions_ticket_refund"),
    )
