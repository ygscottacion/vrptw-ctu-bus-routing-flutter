import logging
import uuid
import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.wallet import Wallet, WalletTransaction, TransactionType
from app.models.ticket import Ticket, TicketStatus
from app.models.location import Location
from app.schemas.ticket import TicketReserveRequest
from app.api.v1.endpoints.tickets import validate_booking_deadline

logger = logging.getLogger(__name__)

TICKET_PRICE_VND = 7000
INITIAL_WALLET_BALANCE_VND = 200000


def create_wallet_for_new_account(db: Session, user_id: uuid.UUID) -> Wallet:
    """Tạo ví ban đầu cho tài khoản mới với số dư mặc định 200,000 VNĐ."""
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if not wallet:
        try:
            wallet = Wallet(user_id=user_id, balance=INITIAL_WALLET_BALANCE_VND)
            db.add(wallet)
            db.commit()
            db.refresh(wallet)
        except IntegrityError:
            db.rollback()
            wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    return wallet


def purchase_ticket(db: Session, user_id: uuid.UUID, ticket_in: TicketReserveRequest) -> Ticket:
    """
    Thực hiện luồng đặt mua vé xe buýt:
    1. Kiểm tra mốc deadline 22:00 giờ VN ngày D-1.
    2. Kiểm tra trùng lịch mua vé.
    3. Kiểm tra số dư ví >= 7,000 VNĐ.
    4. Trừ 7,000 VNĐ, ghi 1 dòng wallet_transactions (type=purchase).
    5. Tạo vé với status = paid_pending_route.
    """
    # 1. Check deadline
    validate_booking_deadline(ticket_in.service_date)

    # 2. Check location
    location = db.query(Location).filter(Location.id == ticket_in.pickup_location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trạm đón đã chọn không tồn tại trên hệ thống.",
        )

    # 3. Check existing ticket for same run
    existing_ticket = db.query(Ticket).filter(
        Ticket.user_id == user_id,
        Ticket.service_date == ticket_in.service_date,
        Ticket.session_id == ticket_in.session_id,
        Ticket.trip_type == ticket_in.trip_type,
        Ticket.status.in_([TicketStatus.PAID_PENDING_ROUTE, TicketStatus.ASSIGNED, TicketStatus.RESERVED]),
    ).first()

    if existing_ticket:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn đã mua vé cho chuyến đi trong ca/chiều này rồi.",
        )

    # 4. Lock & Check wallet balance
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).with_for_update().first()
    if not wallet:
        wallet = create_wallet_for_new_account(db, user_id)
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).with_for_update().first()

    if wallet.balance < TICKET_PRICE_VND:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Số dư ví không đủ để mua vé (Cần {TICKET_PRICE_VND:,} VNĐ, số dư hiện tại: {wallet.balance:,} VNĐ).",
        )

    # 5. Deduct balance & Record purchase
    wallet.balance -= TICKET_PRICE_VND

    qr_code = f"TICKET_{uuid.uuid4().hex[:16].upper()}"
    new_ticket = Ticket(
        id=uuid.uuid4(),
        user_id=user_id,
        route_id=None,
        service_date=ticket_in.service_date,
        session_id=ticket_in.session_id,
        trip_type=ticket_in.trip_type,
        pickup_location_id=ticket_in.pickup_location_id,
        qr_code=qr_code,
        status=TicketStatus.PAID_PENDING_ROUTE,
    )
    db.add(new_ticket)
    db.flush()

    tx = WalletTransaction(
        id=uuid.uuid4(),
        wallet_id=wallet.user_id,
        ticket_id=new_ticket.id,
        type=TransactionType.PURCHASE,
        amount=TICKET_PRICE_VND,
        balance_after=wallet.balance,
        reason="Ticket purchase",
    )
    db.add(tx)

    try:
        db.commit()
        db.refresh(new_ticket)
        return new_ticket
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Đã xảy ra lỗi khi thanh toán vé, vui lòng thử lại.",
        )


def refund_ticket(db: Session, ticket_id: uuid.UUID, reason: str) -> Optional[WalletTransaction]:
    """
    Hàm hoàn tiền TÁI SỬ DỤNG DUY NHẤT cho toàn bộ hệ thống:
    - Trường hợp route_worker không phân được tuyến
    - Trường hợp nhà xe/hệ thống hủy chuyến
    - Trường hợp sinh viên tự hủy vé trước 22:00 D-1
    Bảo vệ bằng khóa unique constraint (ticket_id, type='refund') chống hoàn tiền 2 lần.
    """
    # 1. Lock ticket
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).with_for_update().first()
    if not ticket:
        logger.warning("Refund failed: Ticket %s not found.", ticket_id)
        return None

    # Fast-path idempotency check
    if ticket.status == TicketStatus.REFUNDED:
        logger.info("Ticket %s is already refunded. Idempotent skip.", ticket_id)
        existing_tx = db.query(WalletTransaction).filter(
            WalletTransaction.ticket_id == ticket_id,
            WalletTransaction.type == TransactionType.REFUND,
        ).first()
        return existing_tx

    # 2. Lock wallet
    wallet = db.query(Wallet).filter(Wallet.user_id == ticket.user_id).with_for_update().first()
    if not wallet:
        wallet = create_wallet_for_new_account(db, ticket.user_id)
        wallet = db.query(Wallet).filter(Wallet.user_id == ticket.user_id).with_for_update().first()

    # 3. Update status & credit balance
    ticket.status = TicketStatus.REFUNDED
    wallet.balance += TICKET_PRICE_VND

    tx = WalletTransaction(
        id=uuid.uuid4(),
        wallet_id=wallet.user_id,
        ticket_id=ticket.id,
        type=TransactionType.REFUND,
        amount=TICKET_PRICE_VND,
        balance_after=wallet.balance,
        reason=reason,
    )

    try:
        savepoint = db.begin_nested()
        db.add(tx)
        savepoint.commit()
        db.commit()
        logger.info("Successfully refunded 7,000 VNĐ for ticket %s (reason: %s)", ticket_id, reason)
        return tx
    except IntegrityError as exc:
        db.rollback()
        logger.warning("Refund lock: Duplicate refund attempt for ticket %s blocked by DB constraint: %s", ticket_id, exc)
        # Fetch existing refund transaction gracefully
        existing_tx = db.query(WalletTransaction).filter(
            WalletTransaction.ticket_id == ticket_id,
            WalletTransaction.type == TransactionType.REFUND,
        ).first()
        return existing_tx


def expire_ticket_after_trip(db: Session, ticket_id: uuid.UUID) -> Optional[Ticket]:
    """
    Đánh dấu vé hết hạn khi sinh viên không lên xe (no-show) sau khi ca chạy kết thúc.
    KHÔNG hoàn tiền, KHÔNG tạo giao dịch refund.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        return None

    if ticket.status == TicketStatus.ASSIGNED:
        ticket.status = TicketStatus.EXPIRED
        db.commit()
        db.refresh(ticket)

    return ticket
