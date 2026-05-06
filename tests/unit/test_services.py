"""
Unit tests para service layer.
Pruebas unitarias que validan la lógica de negocio sin dependencias externas.

Categoría: UNITARIAS
Cobertura esperada: >85% de servicios
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


# ==================== TESTS DE USER SERVICE ====================

@pytest.mark.unit
class TestUserServiceUnit:
    """Tests unitarios para user service."""
    
    def test_user_validation_email_required(self):
        """El email es requerido para crear usuario."""
        from app.schemas.user import UserCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UserCreate(nombre="John", password="strongpass")
    
    def test_user_validation_email_formats(self):
        """Validaciones de formato de email (implementación simple en test)."""
        import re

        def is_valid_email(e: str) -> bool:
            pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
            return re.match(pattern, e) is not None

        valid_emails = ["user@example.com", "user.name@example.co.uk", "user+tag@example.com"]
        for e in valid_emails:
            assert is_valid_email(e) is True

        invalid_emails = ["invalid_email", "user@", "@example.com", "user @example.com"]
        for e in invalid_emails:
            assert is_valid_email(e) is False


# ==================== TESTS DE RESTAURANT SERVICE ====================

@pytest.mark.unit
class TestRestaurantServiceUnit:
    """Tests unitarios para restaurant service."""
    
    def test_restaurant_business_hours_validation(self):
        """Validar reglas de horario y capacidad vía schema de RestaurantCreate."""
        from app.schemas.restaurant import RestaurantCreate
        from datetime import time
        from pydantic import ValidationError

        # Horario válido
        rc = RestaurantCreate(
            nombre="R",
            direccion="Calle 1",
            telefono="12345678",
            email="r@test.com",
            hora_apertura=time(9, 0),
            hora_cierre=time(22, 0),
            total_mesas=10,
        )
        assert rc.total_mesas == 10

        # Horario inválido (cierre <= apertura)
        with pytest.raises(ValidationError):
            RestaurantCreate(
                nombre="R",
                direccion="Calle 1",
                telefono="12345678",
                email="r@test.com",
                hora_apertura=time(22, 0),
                hora_cierre=time(9, 0),
                total_mesas=10,
            )
    
    def test_restaurant_capacity_validation(self):
        """Validar que la capacidad sea razonable."""
        from app.schemas.restaurant import RestaurantCreate
        from pydantic import ValidationError

        # Capacidades válidas
        from datetime import time

        rc = RestaurantCreate(
            nombre="R",
            direccion="Calle 1",
            telefono="12345678",
            email="r@test.com",
            hora_apertura=time(9, 0),
            hora_cierre=time(22, 0),
            total_mesas=5,
        )
        assert rc.total_mesas == 5

        # Capacidades inválidas
        from datetime import time

        with pytest.raises(ValidationError):
            RestaurantCreate(
                nombre="R",
                direccion="Calle 1",
                telefono="12345678",
                email="r@test.com",
                hora_apertura=time(9, 0),
                hora_cierre=time(22, 0),
                total_mesas=0,
            )


# ==================== TESTS DE MENU SERVICE ====================

@pytest.mark.unit
class TestMenuServiceUnit:
    """Tests unitarios para menu service."""
    
    def test_menu_price_validation(self):
        """Validaciones básicas del schema `MenuCreate`."""
        from app.schemas.menu import MenuCreate
        from pydantic import ValidationError

        # Precio positivo y tiempo preparación positivo
        with pytest.raises(ValidationError):
            MenuCreate(nombre="X", descripcion="d", precio=0, restaurante_id=1)

        with pytest.raises(ValidationError):
            MenuCreate(nombre="X", descripcion="d", precio=10, tiempo_preparacion=0, restaurante_id=1)


# ==================== TESTS DE ORDER SERVICE ====================

@pytest.mark.unit
class TestOrderServiceUnit:
    """Tests unitarios para order service."""
    
    def test_order_calculation_subtotal(self, factory):
        """Usar `create_order` con DAOs mockeados para verificar subtotal/total."""
        from app.services.order_service import create_order
        from app.schemas.order import OrderCreate, OrderItem

        # Mock DAOs
        menu = Mock()
        menu.precio = 10000
        menu.disponible = True
        menu.restaurante_id = 1

        menu_dao = Mock()
        menu_dao.get_by_id.return_value = menu

        order_dao = Mock()
        order_dao.create.return_value = {"id": 1}

        # Construir el OrderCreate
        oc = OrderCreate(restaurante_id=1, items=[OrderItem(menu_id=1, cantidad=2)])

        result = create_order(order_dao, None, None, menu_dao, oc, usuario_id=2)
        # subtotal debe calcularse como precio * cantidad
        assert order_dao.create.called
        created_payload = order_dao.create.call_args[0][0]
        assert created_payload["subtotal"] == round(float(menu.precio) * 2, 2)
        assert created_payload["total"] == created_payload["subtotal"]


# ==================== TESTS DE RESERVATION SERVICE ====================

@pytest.mark.unit
class TestReservationServiceUnit:
    """Tests unitarios para reservation service."""
    
    def test_reservation_date_validation(self):
        """Probar `check_disponibilidad` y `_asignar_numero_mesa` con DAO mock."""
        from app.services.reservation_service import check_disponibilidad, _asignar_numero_mesa
        from datetime import date

        reservation_dao = Mock()
        # Simular 2 reservas activas en un restaurante que tiene 5 mesas
        reservation_dao.count_reservas_activas.return_value = 2
        assert check_disponibilidad(reservation_dao, restaurante_id=1, fecha=date.today(), total_mesas=5) is True

        # Simular mesas ocupadas
        reservation_dao.get_mesas_ocupadas.return_value = [1, 2, 4]
        assigned = _asignar_numero_mesa(reservation_dao, restaurante_id=1, fecha=date.today(), total_mesas=5)
        assert assigned in {3, 5}


# ==================== TESTS CON MOCKS ====================

@pytest.mark.unit
class TestServiceLayerWithMocks:
    """Tests de service layer usando mocks para dependencias externas."""
    
    def test_service_layer_with_simple_mocks(self):
        """Prueba simple de service layer usando mocks en DAOs"""
        # Probar create_user con DAO mock
        from app.services.user_service import create_user
        dao = Mock()
        dao.get_by_email.return_value = None
        dao.create.return_value = {"id": 1, "email": "new@x.com"}

        from app.schemas.user import UserCreate
        res = create_user(dao, UserCreate(email="a@b.com", nombre="U", password="strongpass"))
        assert dao.create.called
        assert res["email"] == "new@x.com"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
