import datetime
import re

from app.services.ticket_code import generate_ticket_code


def test_ticket_codes_are_short_and_unique(db_session):
    service_date = datetime.date(2026, 10, 4)
    codes = {
        generate_ticket_code(db_session, service_date, "MORNING_1")
        for _ in range(50)
    }

    assert len(codes) == 50
    assert all(re.fullmatch(r"CT-MOR1-041026-[A-Z0-9]{3}", code) for code in codes)


def test_ticket_code_uses_the_selected_session(db_session):
    service_date = datetime.date(2026, 10, 4)

    assert generate_ticket_code(db_session, service_date, "MORNING_2").startswith(
        "CT-MOR2-041026-"
    )
    assert generate_ticket_code(db_session, service_date, "NOON_1").startswith(
        "CT-NOO1-041026-"
    )
