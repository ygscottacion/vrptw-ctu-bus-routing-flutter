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
    Đặt mua vé xe buýt (trừ 7,000 VNĐ từ ví) theo ngày, ca, chiều và trạm đón.
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

    from app.services.wallet_service import purchase_ticket
    new_ticket = purchase_ticket(db=db, user_id=current_profile.id, ticket_in=ticket_in)

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

    return new_ticket


@router.post("/{ticket_id}/cancel", response_model=TicketResponse)
def cancel_ticket(
    ticket_id: uuid.UUID,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    db: Session = Depends(deps.get_db),
    current_profile: Profile = Depends(deps.get_current_student),
) -> Any:
    """
    Hủy vé trước deadline 22:00 ngày D-1 và hoàn lại 7,000 VNĐ vào ví.
    Chỉ cho phép hủy vé ở trạng thái PAID_PENDING_ROUTE (hoặc RESERVED).
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

    if ticket.status in (TicketStatus.REFUNDED, TicketStatus.CANCELLED):
        return ticket

    if ticket.status not in (TicketStatus.PAID_PENDING_ROUTE, TicketStatus.RESERVED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể hủy vé đang ở trạng thái {ticket.status.value}.",
        )

    validate_booking_deadline(ticket.service_date)

    from app.services.wallet_service import refund_ticket
    refund_ticket(db, ticket.id, reason="user_cancelled_before_deadline")

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
    code_str = request.qr_code.strip()

    # 1. Tìm kiếm vé trong CSDL theo qr_code hoặc id (UUID)
    ticket = db.query(Ticket).filter(Ticket.qr_code == code_str).first()
    if not ticket:
        try:
            val_uuid = uuid.UUID(code_str)
            ticket = db.query(Ticket).filter(Ticket.id == val_uuid).first()
        except (ValueError, TypeError):
            pass

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vé không hợp lệ hoặc không tồn tại trong hệ thống.",
        )

    # 2. Kiểm tra trạng thái vé
    if ticket.status == TicketStatus.USED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vé này đã được điểm danh sử dụng trước đó.",
        )

    if ticket.status in (TicketStatus.RESERVED, TicketStatus.PAID_PENDING_ROUTE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vé chưa được hệ thống phân bổ vào tuyến buýt cụ thể.",
        )

    if ticket.status in (TicketStatus.CANCELLED, TicketStatus.REFUNDED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vé này đã bị hủy hoặc hoàn tiền.",
        )

    if ticket.status != TicketStatus.ASSIGNED or not ticket.route_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trạng thái vé không hợp lệ để điểm danh ({ticket.status.value}).",
        )

    # 3. Kiểm tra thông tin tuyến xe và xe buýt
    route = ticket.route
    if not route:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vé chưa có thông tin tuyến xe buýt hợp lệ.",
        )

    from app.models.route import RouteStatus
    if route.status == RouteStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tuyến xe này đã hoàn tất chuyến.",
        )

    # 4. Kiểm tra phân công xe đối với tài xế quét (nếu người quét là Tài xế)
    if current_driver.role == deps.ProfileRole.DRIVER:
        if route.vehicle and route.vehicle.driver_id != current_driver.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vé này thuộc tuyến buýt do tài xế khác phụ trách.",
            )

    student = ticket.user
    student_name = student.full_name if student else "Hành khách"
    student_code = student.phone if student and student.phone else "B2012345"
    route_name = f"Tuyến CT-{str(route.id)[:5].upper()}"

    ticket.status = TicketStatus.USED
    db.commit()
    db.refresh(ticket)

    res = TicketVerifyResponse.model_validate(ticket)
    res.student_name = student_name
    res.student_code = student_code
    res.route_name = route_name
    return res

