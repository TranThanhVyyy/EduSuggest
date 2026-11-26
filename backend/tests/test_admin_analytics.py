from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.dependencies import AuthenticatedPrincipal, get_current_principal
from config.database import get_db
from main import app
from models import NguoiDung, VaiTro
from service import workflow_service


def test_admin_analytics_summary_service_calculation():
    """Unit test verify service logic with mock db session."""
    mock_db = MagicMock()
    # Return counts for total_users, total_courses, total_lessons, total_enrollments, completed_enrollments
    mock_db.scalar.side_effect = [10, 5, 20, 8, 4]

    result = workflow_service.get_admin_analytics_summary(mock_db)

    assert result["total_users"] == 10
    assert result["total_courses"] == 5
    assert result["total_lessons"] == 20
    assert result["total_enrollments"] == 8
    assert result["completed_enrollments"] == 4
    assert result["completion_rate"] == 50.0


def test_admin_analytics_summary_zero_enrollments():
    mock_db = MagicMock()
    mock_db.scalar.side_effect = [0, 0, 0, 0, 0]

    result = workflow_service.get_admin_analytics_summary(mock_db)

    assert result["total_enrollments"] == 0
    assert result["completed_enrollments"] == 0
    assert result["completion_rate"] == 0.0


def test_admin_analytics_endpoint_admin_authorized():
    client = TestClient(app)
    mock_admin = NguoiDung(
        maNguoiDung=999,
        tenTaiKhoan="admin_test",
        hoTen="Admin Test",
        email="admin@test.local",
        vaiTro=VaiTro(maVaiTro=1, tenVaiTro="ADMIN"),
    )

    # Override get_current_principal and db dependency
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        user=mock_admin, token=MagicMock()
    )
    mock_db = MagicMock()
    mock_db.scalar.side_effect = [12, 6, 24, 10, 5]
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.get("/api/admin/analytics/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_users"] == 12
        assert data["total_courses"] == 6
        assert data["total_lessons"] == 24
        assert data["total_enrollments"] == 10
        assert data["completed_enrollments"] == 5
        assert data["completion_rate"] == 50.0
    finally:
        app.dependency_overrides.pop(get_current_principal, None)
        app.dependency_overrides.pop(get_db, None)


def test_admin_analytics_endpoint_unauthorized():
    client = TestClient(app)
    response = client.get("/api/admin/analytics/summary")
    assert response.status_code == 401
