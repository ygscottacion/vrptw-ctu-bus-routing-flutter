from app.crud import crud_user, crud_ticket, crud_incident
from app.schemas.user import UserCreate, UserRole
from app.schemas.incident import IncidentCreate

def test_rbac_get_current_student(db):
    username = "test_student_leader"
    user = crud_user.get_user_by_username(db, username=username)
    if not user:
        user_in = UserCreate(username=username, password="password123", role=UserRole.PASSENGER)
        user = crud_user.create_user(db, user_in=user_in)
    assert user.role == UserRole.PASSENGER

def test_ticket_booking_and_qr_verification(db):
    student_user = crud_user.get_user_by_username(db, username="student1")
    if not student_user:
        user_in = UserCreate(username="student1", password="student123", role=UserRole.PASSENGER)
        student_user = crud_user.create_user(db, user_in=user_in)
    
    # 1. Student books ticket
    ticket = crud_ticket.create_ticket(db=db, user_id=student_user.id)
    assert ticket.id is not None
    assert ticket.qr_code.startswith("CTUBUS-")
    assert ticket.status == "active"

    # 2. Driver verifies student QR ticket
    verified_ticket = crud_ticket.verify_and_use_ticket(db=db, qr_code=ticket.qr_code)
    assert verified_ticket is not None
    assert verified_ticket.status == "used"

def test_incident_reporting_and_resolution(db):
    driver_user = crud_user.get_user_by_username(db, username="driver1")
    if not driver_user:
        user_in = UserCreate(username="driver1", password="password123", role=UserRole.DRIVER)
        driver_user = crud_user.create_user(db, user_in=user_in)
    
    incident_in = IncidentCreate(title="Tắc đường Chợ Cái Răng", description="Xe di chuyển chậm 15 phút")
    incident = crud_incident.create_incident(db=db, driver_id=driver_user.id, incident_in=incident_in)
    assert incident.id is not None
    assert incident.status == "pending"

    # Admin updates incident status to resolved
    updated = crud_incident.update_incident_status(db=db, incident_id=incident.id, status="resolved")
    assert updated.status == "resolved"
