"""
Tests esenciales para user_service.py.
Se enfocan en las rutas de negocio más importantes.
"""

from unittest.mock import Mock, patch
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models.user import RoleEnum, User
from app.schemas.user import UserCreate
from app.services import user_service


def _user(user_id: int, email: str, role: RoleEnum) -> User:
    return User(
        id=user_id,
        email=email,
        nombre="Usuario",
        password_hash="hash",
        rol=role,
        activo=True,
    )


# Pruebas de creación de usuario y validación de email duplicado.
class TestCreateUser:
    def test_create_user_when_email_does_not_exist(self):
        # Verifica que el usuario se crea exitosamente cuando el email no existe
        dao = Mock()
        dao.get_by_email.return_value = None
        dao.create.return_value = _user(11, "nuevo@demo.com", RoleEnum.CLIENTE)

        result = user_service.create_user(
            dao,
            UserCreate(email="nuevo@demo.com", nombre="Nuevo Usuario", rol=RoleEnum.CLIENTE, password="secret123"),
        )

        assert result.email == "nuevo@demo.com"
        dao.create.assert_called_once()

    def test_create_user_returns_none_when_email_exists(self):
        # Verifica que create_user devuelve None si el email ya existe
        dao = Mock()
        dao.get_by_email.return_value = _user(1, "admin@demo.com", RoleEnum.ADMIN)

        result = user_service.create_user(
            dao,
            UserCreate(email="admin@demo.com", nombre="Duplicado", rol=RoleEnum.CLIENTE, password="secret123"),
        )

        assert result is None
        dao.create.assert_not_called()


# Pruebas de permisos para actualizar y eliminar usuarios.
class TestPermissions:
    def test_owner_can_update_or_delete_own_account(self):
        # Verifica que un usuario puede actualizar/eliminar su propia cuenta
        current_user = _user(1, "admin@demo.com", RoleEnum.ADMIN)
        target_user = _user(1, "admin@demo.com", RoleEnum.ADMIN)

        user_service.validate_update_permissions(current_user, target_user, None)
        user_service.validate_delete_permissions(current_user, target_user, None)

    def test_unauthenticated_user_is_rejected(self):
        # Verifica que un usuario no autenticado (None) es rechazado con error 401
        target_user = _user(1, "admin@demo.com", RoleEnum.ADMIN)

        with pytest.raises(HTTPException) as exc_info:
            user_service.validate_update_permissions(None, target_user, None)
        assert exc_info.value.status_code == 401

    def test_regular_user_cannot_modify_other_user(self):
        # Verifica que un cliente no puede eliminar la cuenta de otro cliente
        current_user = _user(2, "cliente1@demo.com", RoleEnum.CLIENTE)
        target_user = _user(4, "cliente2@demo.com", RoleEnum.CLIENTE)

        with pytest.raises(HTTPException) as exc_info:
            user_service.validate_delete_permissions(current_user, target_user, None)
        assert exc_info.value.status_code == 403

    def test_admin_needs_master_code_for_other_user(self):
        # Verifica que admin debe proporcionar código maestro para actualizar otro usuario
        current_user = _user(1, "admin@demo.com", RoleEnum.ADMIN)
        target_user = _user(2, "cliente1@demo.com", RoleEnum.CLIENTE)

        with patch.object(user_service.settings, "MASTER_ADMIN_CODE", "secret123"):
            with pytest.raises(HTTPException) as exc_info:
                user_service.validate_update_permissions(current_user, target_user, "wrong")

        assert exc_info.value.status_code == 403

    def test_delete_permissions_unauthenticated_is_rejected(self):
        # Verifica que usuario no autenticado es rechazado al eliminar (error 401)
        target_user = _user(2, "x@x.com", RoleEnum.CLIENTE)
        with pytest.raises(HTTPException) as exc_info:
            user_service.validate_delete_permissions(None, target_user, None)
        assert exc_info.value.status_code == 401

    def test_admin_without_master_code_for_delete_is_rejected(self):
        # Verifica que admin sin código maestro no puede eliminar otro usuario
        current_user = _user(1, "admin@demo.com", RoleEnum.ADMIN)
        target_user = _user(2, "cliente@demo.com", RoleEnum.CLIENTE)

        with patch.object(user_service.settings, "MASTER_ADMIN_CODE", None):
            with pytest.raises(HTTPException) as exc_info:
                user_service.validate_delete_permissions(current_user, target_user, None)

        assert exc_info.value.status_code == 403

    def test_admin_with_correct_master_code_allows_update_and_delete(self):
        # Verifica que admin con código maestro correcto puede actualizar/eliminar otro usuario
        current_user = _user(1, "admin@demo.com", RoleEnum.ADMIN)
        target_user = _user(2, "cliente@demo.com", RoleEnum.CLIENTE)

        with patch.object(user_service.settings, "MASTER_ADMIN_CODE", "supersecret"):
            # should not raise
            user_service.validate_update_permissions(current_user, target_user, "supersecret")
            user_service.validate_delete_permissions(current_user, target_user, "supersecret")


# Pruebas de resolución de datos desde Cognito y del usuario local.
class TestCognitoResolution:
    def test_resolve_current_user_email_from_jwt(self):
        # Verifica que extrae email directamente del JWT cuando está disponible
        assert user_service.resolve_current_user_email({"email": "user@example.com"}) == "user@example.com"

    def test_resolve_current_user_email_via_cognito_username(self):
        # Verifica que resuelve email desde Cognito usando username cuando JWT no tiene email
        with patch.object(
            user_service._cognito_client.client,
            "admin_get_user",
            return_value={"UserAttributes": [{"Name": "email", "Value": "user@example.com"}]},
        ):
            result = user_service.resolve_current_user_email({"username": "user-123"})

        assert result == "user@example.com"

    def test_resolve_current_local_user_id_from_jwt_id(self):
        # Verifica que resuelve usuario_id directamente del JWT cuando está disponible
        dao = Mock()
        result = user_service.resolve_current_local_user_id({"usuario_id": "5"}, dao)

        assert result == 5
        dao.get_by_email.assert_not_called()

    def test_resolve_current_local_user_id_from_email_lookup(self):
        # Verifica que busca usuario por email en BD cuando JWT no tiene usuario_id
        dao = Mock()
        dao.get_by_email.return_value = _user(2, "cliente1@demo.com", RoleEnum.CLIENTE)

        result = user_service.resolve_current_local_user_id({"email": "cliente1@demo.com"}, dao)

        assert result == 2

    def test_resolve_current_local_user_returns_user(self):
        # Verifica que obtiene el usuario completo de BD usando usuario_id del JWT
        dao = Mock()
        dao.get_by_id.return_value = _user(2, "cliente1@demo.com", RoleEnum.CLIENTE)

        result = user_service.resolve_current_local_user({"usuario_id": "2"}, dao)

        assert result.email == "cliente1@demo.com"

    def test_extract_email_from_cognito_user_returns_none_when_missing(self):
        # Verifica que retorna None cuando el atributo email no existe en respuesta de Cognito
        resp = {"UserAttributes": [{"Name": "name", "Value": "noemail"}]}
        assert user_service.extract_email_from_cognito_user(resp) is None

    def test_resolve_cognito_username_uses_cognito_key(self):
        # Verifica que extrae username usando la clave 'cognito:username' del JWT
        data = {"cognito:username": "cog-user"}
        assert user_service.resolve_cognito_username(data) == "cog-user"

    def test_resolve_current_user_email_username_contains_at(self):
        # Verifica que trata username como email si contiene @ para casos especiales
        assert user_service.resolve_current_user_email({"username": "me@example.com"}) == "me@example.com"

    def test_sync_email_cognito_raises_http_exception_on_error(self, monkeypatch):
        # Verifica que lanza error HTTP 502 cuando falla sincronización con Cognito
        def raise_err(old, new):
            raise Exception("boom")

        monkeypatch.setattr(user_service, "_cognito_client", SimpleNamespace(update_user_email=raise_err))

        with pytest.raises(HTTPException) as exc_info:
            user_service.sync_email_cognito("a@b.com", "c@d.com")

        assert exc_info.value.status_code == 502

    def test_resolve_current_local_user_id_handles_admin_get_user_exception_and_lookup(self, monkeypatch):
        # Verifica que si admin_get_user falla, intenta buscar por email en BD local
        dao = Mock()
        dao.get_by_email.return_value = _user(77, "lookup@demo.com", RoleEnum.CLIENTE)

        class FakeClient:
            def admin_get_user(self, **kwargs):
                raise Exception("down")
        # patch the global cognito client using pytest monkeypatch fixture
        monkeypatch.setattr(user_service, "_cognito_client", SimpleNamespace(client=FakeClient()))
        result = user_service.resolve_current_local_user_id({"username": "lookup@demo.com"}, dao)

        assert result == 77

    def test_validate_update_permissions_rejects_non_owner_non_admin(self):
        # Verifica que usuario regular no puede actualizar cuenta de otro usuario regular
        current_user = _user(2, "a@b.com", RoleEnum.CLIENTE)
        target_user = _user(3, "c@d.com", RoleEnum.CLIENTE)

        with pytest.raises(HTTPException) as exc_info:
            user_service.validate_update_permissions(current_user, target_user, None)

        assert exc_info.value.status_code == 403

    def test_admin_without_master_code_for_update_is_rejected(self):
        # Verifica que admin sin código maestro no puede actualizar otro usuario
        current_user = _user(1, "admin@demo.com", RoleEnum.ADMIN)
        target_user = _user(2, "cliente@demo.com", RoleEnum.CLIENTE)

        with patch.object(user_service.settings, "MASTER_ADMIN_CODE", None):
            with pytest.raises(HTTPException) as exc_info:
                user_service.validate_update_permissions(current_user, target_user, None)

        assert exc_info.value.status_code == 403

    def test_resolve_current_local_user_id_uses_sub_when_usuario_id_invalid(self):
        # Verifica que usa 'sub' como fallback cuando 'usuario_id' no es un número válido
        dao = Mock()
        result = user_service.resolve_current_local_user_id({"usuario_id": "notint", "sub": "42"}, dao)

        assert result == 42

    def test_resolve_current_local_user_id_returns_none_when_no_identifiers(self):
        # Verifica que retorna None cuando JWT no contiene usuario_id, email ni sub
        dao = Mock()
        result = user_service.resolve_current_local_user_id({}, dao)

        assert result is None

    def test_resolve_current_local_user_id_admin_get_user_returns_email_but_no_local(self, monkeypatch):
        # Verifica que retorna None si Cognito devuelve email pero no existe usuario en BD local
        dao = Mock()
        dao.get_by_email.return_value = None

        monkeypatch.setattr(
            user_service,
            "_cognito_client",
            SimpleNamespace(client=SimpleNamespace(admin_get_user=lambda **kw: {"UserAttributes": [{"Name": "email", "Value": "found@demo.com"}]})),
        )

        result = user_service.resolve_current_local_user_id({"username": "someuser"}, dao)
        assert result is None

    def test_resolve_current_user_email_admin_get_user_returns_none_when_no_email(self, monkeypatch):
        # Verifica que retorna None si Cognito responde sin atributo email
        monkeypatch.setattr(
            user_service,
            "_cognito_client",
            SimpleNamespace(client=SimpleNamespace(admin_get_user=lambda **kw: {"UserAttributes": [{"Name": "nickname", "Value": "x"}]})),
        )

        res = user_service.resolve_current_user_email({"username": "noemailuser"})
        assert res is None

    def test_resolve_current_user_email_returns_none_when_no_username_or_email(self):
        # Verifica que retorna None cuando JWT está vacío sin email ni username
        assert user_service.resolve_current_user_email({}) is None

    def test_resolve_current_local_user_with_valid_email_in_db(self):
        # Verifica que obtiene usuario local completo usando email cuando usuario_id no disponible
        dao = Mock()
        dao.get_by_id.return_value = None
        dao.get_by_email.return_value = _user(5, "test@example.com", RoleEnum.CLIENTE)

        result = user_service.resolve_current_local_user({"email": "test@example.com"}, dao)

        assert result is not None
        assert result.id == 5
        assert result.email == "test@example.com"

    def test_resolve_current_user_email_when_cognito_fails_with_username(self, monkeypatch):
        # Verifica que cuando Cognito falla completamente, intenta usar username como email si contiene @
        def raise_err(**kwargs):
            raise Exception("Cognito down")

        monkeypatch.setattr(
            user_service,
            "_cognito_client",
            SimpleNamespace(client=SimpleNamespace(admin_get_user=raise_err)),
        )

        # Username con @ debe ser retornado como email
        result = user_service.resolve_current_user_email({"username": "user@example.com"})
        assert result == "user@example.com"
