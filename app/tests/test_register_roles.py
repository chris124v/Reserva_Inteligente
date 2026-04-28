from unittest.mock import patch

from app.models.user import RoleEnum, User


def test_register_admin_requiere_codigo_si_configurado(client, test_db):
    from app.routes import auth as auth_routes

    with patch.object(auth_routes.settings, "ADMIN_REGISTRATION_CODE", "secret"), \
         patch.object(auth_routes.cognito_client, "register_user") as mock_register:
        mock_register.return_value = {"success": True, "message": "ok"}

        r = client.post(
            "/auth/register",
            json={
                "email": "admin1@test.com",
                "password": "Pass123!",
                "nombre": "Admin Uno",
                "rol": "admin",
            },
        )

    assert r.status_code == 403
    assert "Código" in r.json()["detail"]
    assert test_db.query(User).filter(User.email == "admin1@test.com").first() is None
    mock_register.assert_not_called()


def test_register_admin_ok_con_codigo(client, test_db):
    from app.routes import auth as auth_routes

    with patch.object(auth_routes.settings, "ADMIN_REGISTRATION_CODE", "secret"), \
         patch.object(auth_routes.cognito_client, "register_user") as mock_register:
        mock_register.return_value = {"success": True, "message": "ok"}

        r = client.post(
            "/auth/register",
            json={
                "email": "admin2@test.com",
                "password": "Pass123!",
                "nombre": "Admin Dos",
                "rol": "admin",
                "admin_code": "secret",
            },
        )

    assert r.status_code == 200

    local_user = test_db.query(User).filter(User.email == "admin2@test.com").first()
    assert local_user is not None
    assert local_user.rol == RoleEnum.ADMIN

    mock_register.assert_called_once()
