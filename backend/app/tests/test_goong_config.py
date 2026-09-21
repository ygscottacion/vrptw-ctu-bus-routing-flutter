import pytest
from app.core.config import Settings

def test_goong_config_validation_success():
    s = Settings(
        GOONG_API_KEY="7WSy0ek8OLEv1HZvB9oikhHT6hVrohUdCLShbK8S",
        ENVIRONMENT="production"
    )
    # Should not raise any error
    s.validate_goong_config()

def test_goong_config_validation_fail_fast_prod():
    s = Settings(
        GOONG_API_KEY="",
        ENVIRONMENT="production"
    )
    with pytest.raises(ValueError, match="CRITICAL: GOONG_API_KEY is missing"):
        s.validate_goong_config()

def test_goong_config_validation_warning_dev(caplog):
    s = Settings(
        GOONG_API_KEY="",
        ENVIRONMENT="development"
    )
    s.validate_goong_config()
    assert "GOONG_API_KEY is not configured" in caplog.text
