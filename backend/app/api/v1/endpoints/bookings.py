from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.models.booking import Booking, BookingStatus
from app.models.ticket import Ticket, TicketStatus
from app.models.route import Route, RouteStop
from app.schemas.booking import BookingCreate, BookingResponse, BookingUpdate

router = APIRouter()

@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking_in: BookingCreate,
    db: Session = Depends(deps.get_db),
    current_student: User = Depends(deps.get_current_student)
) -> Any:
    # 1. Kiểm tra vé thuộc sở hữu của sinh viên
    ticket = db.query(Ticket).filter(
        Ticket.id == booking_in.ticket_id,
        Ticket.user_id == current_student.id
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Không tìm thấy vé trong ví của bạn.")

    # 2. Kiểm tra vé phải đang ACTIVE
    if ticket.status != TicketStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Vé không còn hiệu lực.")

    # 3. Kiểm tra vé đã được dùng giữ chỗ cho chuyến khác chưa
    if ticket.route_id is not None:
        raise HTTPException(status_code=400, detail="Vé này đã được dùng để đặt một chuyến đi khác.")

    # 4. Kiểm tra tuyến xe tồn tại
    route = db.query(Route).filter(Route.id == booking_in.route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Không tìm thấy tuyến xe đã chọn.")

    # 5. KIỂM TRA TRẠM ĐÓN HỢP LỆ (Trạm phải thuộc lộ trình của Tuyến xe này)
    valid_stop = db.query(RouteStop).filter(
        RouteStop.route_id == booking_in.route_id,
        RouteStop.location_id == booking_in.pickup_location_id
    ).first()

    if not valid_stop:
        raise HTTPException(status_code=400, detail="Trạm đón này không nằm trong lộ trình của tuyến xe đã chọn.")

    # 6. TỰ ĐỘNG XỬ LÝ THỜI GIAN ĐÓN
    # Lấy arrival_time từ trạm. Nếu chưa có (chưa chạy solver xong) -> Gán chuỗi "Đang chờ cập nhật"
    stop_arrival_time = getattr(valid_stop, 'arrival_time', None)
    final_schedule_time = str(stop_arrival_time) if stop_arrival_time else "Đang chờ cập nhật"

    # 7. Khởi tạo đơn đặt chuyến
    new_booking = Booking(
        user_id=current_student.id,
        route_id=booking_in.route_id,
        ticket_id=booking_in.ticket_id,
        pickup_location_id=booking_in.pickup_location_id,
        schedule_time=final_schedule_time,
        note=booking_in.note,
        status=BookingStatus.CONFIRMED
    )
    db.add(new_booking)

    # 8. Gán chuyến đi vào vé nhưng GIỮ NGUYÊN trạng thái TicketStatus.ACTIVE
    ticket.route_id = booking_in.route_id

    db.commit()
    db.refresh(new_booking)
    return new_booking


@router.get("/me", response_model=List[BookingResponse])
def read_my_bookings(
    db: Session = Depends(deps.get_db),
    current_student: User = Depends(deps.get_current_student)
) -> Any:
    return db.query(Booking).filter(Booking.user_id == current_student.id).all()


@router.put("/{booking_id}", response_model=BookingResponse)
def update_booking(
    booking_id: int,
    booking_in: BookingUpdate,
    db: Session = Depends(deps.get_db),
    current_student: User = Depends(deps.get_current_student)
) -> Any:
    """
    Cho phép sinh viên chỉnh sửa tuyến đường, trạm đón hoặc ghi chú của chuyến đi.
    """
    # 1. Tìm đơn đặt chuyến của sinh viên
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.user_id == current_student.id
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin đặt chuyến.")

    # 2. Chỉ cho phép sửa khi chuyến đi chưa hoàn thành
    if booking.status != BookingStatus.CONFIRMED:
        raise HTTPException(status_code=400, detail="Chỉ có thể chỉnh sửa chuyến đi đang ở trạng thái chờ.")

    # Xác định tuyến và trạm mục tiêu (lấy giá trị mới truyền lên, nếu không có thì giữ cũ)
    target_route_id = booking_in.route_id if booking_in.route_id is not None else booking.route_id
    target_location_id = booking_in.pickup_location_id if booking_in.pickup_location_id is not None else booking.pickup_location_id

    # 3. Nếu có cập nhật Route hoặc Trạm đón -> Cần xác thực lại lộ trình & giờ đón
    if booking_in.route_id is not None or booking_in.pickup_location_id is not None:
        valid_stop = db.query(RouteStop).filter(
            RouteStop.route_id == target_route_id,
            RouteStop.location_id == target_location_id
        ).first()

        if not valid_stop:
            raise HTTPException(status_code=400, detail="Trạm đón không nằm trong lộ trình của tuyến xe đã chọn.")

        stop_arrival_time = getattr(valid_stop, 'arrival_time', None)
        booking.schedule_time = str(stop_arrival_time) if stop_arrival_time else "Đang chờ cập nhật"
        booking.route_id = target_route_id
        booking.pickup_location_id = target_location_id

        # Đổi route_id trong Booking thì đổi luôn route_id của Vé
        ticket = db.query(Ticket).filter(Ticket.id == booking.ticket_id).first()
        if ticket:
            ticket.route_id = target_route_id

    if booking_in.note is not None:
        booking.note = booking_in.note

    db.commit()
    db.refresh(booking)
    return booking