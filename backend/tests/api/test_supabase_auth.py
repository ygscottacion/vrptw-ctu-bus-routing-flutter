import concurrent.futures
import datetime
import uuid
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jose import jwk, jwt
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import deps
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.models.profile import Profile, ProfileRole

client = TestClient(app)

# Generate an RSA Key Pair for RS256 JWT Testing
_private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
_pem_private = _private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
_public_key = _private_key.public_key()
_pem_public = _public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)

# Convert RSA Public key to JWK
_jwk_dict = jwk.construct(_pem_public, algorithm="RS256").to_dict()
_jwk_dict["kid"] = "test-key-id-1"
_jwk_dict["use"] = "sig"

TEST_JWKS = {"keys": [_jwk_dict]}

# Set up settings and mock JWKS cache
TEST_SUPABASE_URL = "https://test-supabase-project.supabase.co"
settings.SUPABASE_URL = TEST_SUPABASE_URL
settings.SUPABASE_JWT_SECRET = "test_supabase_jwt_secret_hs256_12345"

deps._jwks_cache[settings.SUPABASE_JWKS_URL] = TEST_JWKS


def make_token(
    sub: str,
    role: str = "authenticated",
    iss: str = f"{TEST_SUPABASE_URL}/auth/v1",
    aud: str = "authenticated",
    exp_delta_seconds: int = 3600,
    alg: str = "RS256",
    key_to_use: bytes = _pem_private,
    kid: str = "test-key-id-1",
    extra_claims: dict = None,
) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    claims = {
        "sub": sub,
        "role": role,
        "iss": iss,
        "aud": aud,
        "iat": int(now.timestamp()),
        "exp": int((now + datetime.timedelta(seconds=exp_delta_seconds)).timestamp()),
        "email": f"user_{sub[:8]}@example.com",
    }
    if extra_claims:
        claims.update(extra_claims)

    headers = {"kid": kid} if alg.startswith("RS") else {}
    return jwt.encode(claims, key_to_use, algorithm=alg, headers=headers)


def ensure_auth_user(db_session: Session, user_id: uuid.UUID):
    try:
        db_session.execute(
            text("INSERT INTO auth.users (id, aud, role) VALUES (:id, 'authenticated', 'authenticated') ON CONFLICT (id) DO NOTHING"),
            {"id": str(user_id)},
        )
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_valid_jwt_returns_profile_me(db_session: Session):
    user_id = uuid.uuid4()
    token = make_token(sub=str(user_id))

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user_id)
    assert data["role"] == "passenger"
    assert "email" in data


def test_role_guards_passenger(db_session: Session):
    user_id = uuid.uuid4()
    ensure_auth_user(db_session, user_id)

    profile = Profile(id=user_id, role=ProfileRole.PASSENGER, full_name="Student Test")
    db_session.add(profile)
    db_session.commit()

    token = make_token(sub=str(user_id))

    profile_req = deps.get_current_student(
        current_profile=deps.get_current_profile(db=db_session, token=token)
    )
    assert profile_req.role == ProfileRole.PASSENGER

    with pytest.raises(Exception) as exc_info:
        deps.get_current_driver(
            current_profile=deps.get_current_profile(db=db_session, token=token)
        )
    assert exc_info.value.status_code == 403

    with pytest.raises(Exception) as exc_info:
        deps.get_current_admin(
            current_profile=deps.get_current_profile(db=db_session, token=token)
        )
    assert exc_info.value.status_code == 403


def test_role_guards_driver(db_session: Session):
    user_id = uuid.uuid4()
    ensure_auth_user(db_session, user_id)

    profile = Profile(id=user_id, role=ProfileRole.DRIVER, full_name="Driver Test")
    db_session.add(profile)
    db_session.commit()

    token = make_token(sub=str(user_id))
    cur_profile = deps.get_current_profile(db=db_session, token=token)

    drv_profile = deps.get_current_driver(current_profile=cur_profile)
    assert drv_profile.role == ProfileRole.DRIVER

    with pytest.raises(Exception) as exc_info:
        deps.get_current_admin(current_profile=cur_profile)
    assert exc_info.value.status_code == 403


def test_role_guards_admin(db_session: Session):
    user_id = uuid.uuid4()
    ensure_auth_user(db_session, user_id)

    profile = Profile(id=user_id, role=ProfileRole.ADMIN, full_name="Admin Test")
    db_session.add(profile)
    db_session.commit()

    token = make_token(sub=str(user_id))
    cur_profile = deps.get_current_profile(db=db_session, token=token)

    assert deps.get_current_student(current_profile=cur_profile).role == ProfileRole.ADMIN
    assert deps.get_current_driver(current_profile=cur_profile).role == ProfileRole.ADMIN
    assert deps.get_current_admin(current_profile=cur_profile).role == ProfileRole.ADMIN


def test_invalid_tokens_return_401(db_session: Session):
    user_id = str(uuid.uuid4())

    expired_token = make_token(sub=user_id, exp_delta_seconds=-10)
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401

    other_priv_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other_priv_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    bad_sig_token = make_token(sub=user_id, key_to_use=other_pem)
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad_sig_token}"})
    assert res.status_code == 401

    wrong_iss_token = make_token(sub=user_id, iss="https://hacker.com/auth/v1")
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {wrong_iss_token}"})
    assert res.status_code == 401

    wrong_aud_token = make_token(sub=user_id, aud="anon")
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {wrong_aud_token}"})
    assert res.status_code == 401

    no_sub_token = jwt.encode(
        {"iss": f"{TEST_SUPABASE_URL}/auth/v1", "aud": "authenticated", "exp": 9999999999},
        _pem_private,
        algorithm="RS256",
        headers={"kid": "test-key-id-1"},
    )
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {no_sub_token}"})
    assert res.status_code == 401

    invalid_uuid_token = make_token(sub="not-a-uuid-string")
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {invalid_uuid_token}"})
    assert res.status_code == 401


def test_auto_create_passenger_profile_if_missing(db_session: Session):
    new_user_id = uuid.uuid4()
    existing = db_session.query(Profile).filter(Profile.id == new_user_id).first()
    assert existing is None

    token = make_token(sub=str(new_user_id))
    profile = deps.get_current_profile(db=db_session, token=token)

    assert profile.id == new_user_id
    assert profile.role == ProfileRole.PASSENGER

    db_profile = db_session.query(Profile).filter(Profile.id == new_user_id).first()
    assert db_profile is not None
    assert db_profile.role == ProfileRole.PASSENGER


def test_concurrent_auto_create_profile():
    new_user_id = uuid.uuid4()
    token = make_token(sub=str(new_user_id))

    def fetch_profile():
        session = SessionLocal()
        try:
            p = deps.get_current_profile(db=session, token=token)
            return p.id
        finally:
            session.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_profile) for _ in range(5)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 5
    assert all(r == new_user_id for r in results)

    session = SessionLocal()
    count = session.query(Profile).filter(Profile.id == new_user_id).count()
    session.close()
    assert count == 1
