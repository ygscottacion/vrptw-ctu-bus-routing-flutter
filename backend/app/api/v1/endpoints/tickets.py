import uuid
import datetime
from zoneinfo import ZoneInfo
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api import deps
from app.core.idempotency import process_idempotency_key, save_idempotency_key
from app.models.profile import Profile
from app.models.location import Location
from app.models.ticket import Ticket, TicketStatus
from app.schemas.ticket import TicketReserveRequest, TicketResponse, QRVerifyRequest, TicketVerifyResponse

router = APIRouter()

from app.core.timezone import VN_TZ


def validate_booking_deadline(service_date: datetime.date) -> None:
    """
    Validates cutoff deadline at 22:00 Asia/Ho_Chi_Minh on (service_date - 1 day).
    Rejects past service dates or requests made after 22:00 on D-1.
    """
    now_vn = datetime.datetime.now(VN_TZ)
    today_vn = now_vn.date()

    if service_date <= today_vn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ có thể đặt vé cho các ngày chạy trong tương lai.",
        )

    cutoff_dt = datetime.datetime.combine(
        service_date - datetime.timedelta(days=1),
        datetime.time(hour=22, minute=0, second=0),
        tzinfo=VN_TZ,
    )

    if now_vn >= cutoff_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Đã quá hạn đặt vé 22:00 (giờ Việt Nam) của ngày trước ngày chạy.",
        )


@router.post("/reserve", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def reserve_ticket(
    ticket_in: TicketReserveRequest,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    db: Session = Depends(deps.get_db),
    current_profile: Profile = Depends(deps.get_current_student),
) -> Any:
    """
    Giữ chỗ vé xe buýt theo ngày, ca, chiều và trạm đón.
    Chỉ áp dụng trước 22:00 (Asia/Ho_Chi_Minh) ngày hôm trước.
    """
    endpoint = "/api/v1/tickets/reserve"
    existing_idempotency, req_hash = process_idempotency_key(
        db=db,
        user_id=current_profile.id,
        endpoint=endpoint,
        key=x_idempotency_key,
        request_data=ticket_in.model_dump(),
    )

    if existing_idempotency:
        return Response(
            content=existing_idempotency.response_body if isinstance(existing_idempotency.response_body, str) else None,
            status_code=existing_idempotency.response_code,
            media_type="application/json",
        ) if not isinstance(existing_idempotency.response_body, dict) else existing_idempotency.response_body

    # 1. Validate deadline
    validate_booking_deadline(ticket_in.service_date)

    # 2. Check location
    location = db.query(Location).filter(Location.id == ticket_in.pickup_location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trạm đón đã chọn không tồn tại trên hệ thống.",
        )

    # 3. Check existing reservation in DB transaction
    existing_ticket = db.query(Ticket).filter(
        Ticket.user_id == current_profile.id,
        Ticket.service_date == ticket_in.service_date,
        Ticket.session_id == ticket_in.session_id,
        Ticket.trip_type == ticket_in.trip_type,
        Ticket.status.in_([TicketStatus.RESERVED, TicketStatus.ASSIGNED]),
    ).first()

    if existing_ticket:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn đã giữ chỗ cho chuyến đi này rồi.",
        )

    qr_code = f"TICKET_{uuid.uuid4().hex[:16].upper()}"

    new_ticket = Ticket(
        id=uuid.uuid4(),
        user_id=current_profile.id,
        route_id=None,
        service_date=ticket_in.service_date,
        session_id=ticket_in.session_id,
        trip_type=ticket_in.trip_type,
        pickup_location_id=ticket_in.pickup_location_id,
        qr_code=qr_code,
        status=TicketStatus.RESERVED,
    )

    try:
        db.add(new_ticket)
        db.flush()

        response_schema = TicketResponse.model_validate(new_ticket)
        response_dict = response_schema.model_dump(mode="json")

        if x_idempotency_key and req_hash:
            save_idempotency_key(
                db=db,
                user_id=current_profile.id,
                endpoint=endpoint,
                key=x_idempotency_key,
                request_hash=req_hash,
                response_code=status.HTTP_201_CREATED,
                response_body=response_dict,
            )

        db.commit()
        db.refresh(new_ticket)
        return new_ticket
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn đã giữ chỗ cho lượt xe trong ca/chiều này rồi.",
        )


@router.post("/{ticket_id}/cancel", response_model=TicketResponse)
def cancel_ticket(
    ticket_id: uuid.UUID,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    db: Session = Depends(deps.get_db),
    current_profile: Profile = Depends(deps.get_current_student),
) -> Any:
    """
    Hủy lượt giữ chỗ vé trước deadline 22:00 ngày D-1.
    Chỉ cho phép hủy vé ở trạng thái RESERVED.
    """
    endpoint = f"/api/v1/tickets/{ticket_id}/cancel"
    existing_idempotency, req_hash = process_idempotency_key(
        db=db,
        user_id=current_profile.id,
        endpoint=endpoint,
        key=x_idempotency_key,
        request_data={"ticket_id": str(ticket_id)},
    )

    if existing_idempotency:
        return existing_idempotency.response_body

    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id,
        Ticket.user_id == current_profile.id,
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy vé trong danh sách của bạn.",
        )

    if ticket.status == TicketStatus.CANCELLED:
        return ticket

    if ticket.status != TicketStatus.RESERVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể hủy vé đang ở trạng thái {ticket.status.value}.",
        )

    validate_booking_deadline(ticket.service_date)

    ticket.status = TicketStatus.CANCELLED

    response_schema = TicketResponse.model_validate(ticket)
    response_dict = response_schema.model_dump(mode="json")

    if x_idempotency_key and req_hash:
        save_idempotency_key(
            db=db,
            user_id=current_profile.id,
            endpoint=endpoint,
            key=x_idempotency_key,
            request_hash=req_hash,
            response_code=status.HTTP_200_OK,
            response_body=response_dict,
        )

    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/me", response_model=List[TicketResponse])
def read_my_tickets(
    db: Session = Depends(deps.get_db),
    current_profile: Profile = Depends(deps.get_current_student),
) -> Any:
    """Lấy danh sách tất cả các vé của sinh viên hiện tại."""
    return db.query(Ticket).filter(Ticket.user_id == current_profile.id).order_by(Ticket.created_at.desc()).all()


@router.post("/verify-qr", response_model=TicketVerifyResponse)
def verify_ticket_qr(
    request: QRVerifyRequest,
    db: Session = Depends(deps.get_db),
    current_driver: Profile = Depends(deps.get_current_driver),
) -> Any:
    """Tài xế quét mã QR trên xe để xác nhận hành khách lên xe."""
    ticket = db.query(Ticket).filter(Ticket.qr_code == request.qr_code).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vé không hợp lệ hoặc không tồn tại trong hệ thống.",
        )

    if ticket.status == TicketStatus.USED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vé này đã được điểm danh trước đó.",
        )

    if ticket.status not in (TicketStatus.ASSIGNED, TicketStatus.RESERVED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vé không ở trạng thái hợp lệ để điểm danh ({ticket.status.value}).",
        )

    student = ticket.user
    route = ticket.route

    student_name = student.full_name if student else "Hành khách"
    student_code = student.phone if student and student.phone else "B2012345"
    route_name = f"Tuyến CT-{str(route.id)[:5].upper()}" if route else "Lượt chưa phân tuyến"

    ticket.status = TicketStatus.USED
    db.commit()
    db.refresh(ticket)

    res = TicketVerifyResponse.model_validate(ticket)
    res.student_name = student_name
    res.student_code = student_code
    res.route_name = route_name
    return res
