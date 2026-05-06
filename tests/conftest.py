"""
Configuración global para tests en tests/
Fixtures compartidas para unit tests e integration tests.
"""

import pytest
import json
from pathlib import Path

# Si la librería `redis` no está instalada en el entorno de tests,
# inyectamos un mock mínimo en `sys.modules` para evitar errores de import
import sys
from types import SimpleNamespace

if "redis" not in sys.modules:
    class _FakeRedisClient:
        def __init__(self, *a, **k):
            pass
        def get(self, key):
            return None
        def setex(self, key, ttl, val):
            return None
        def delete(self, *keys):
            return None
        def keys(self, pattern):
            return []

    def _fake_redis_Redis(*a, **k):
        return _FakeRedisClient()

    sys.modules["redis"] = SimpleNamespace(Redis=_fake_redis_Redis)


def generate_all_test_data(export: bool = False):
    """Cargar datos desde `tests/data/*.json` si existen.
    Si no existen, devuelve un conjunto mínimo de datos para permitir
    la ejecución de tests unitarios que dependen de `generated_test_data`.
    """
    base = Path(__file__).parent / "data"
    def _load_or_default(name, default):
        p = base / name
        if p.exists():
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default

    users = _load_or_default('users.json', [{"id": 1, "email": "admin@test.com", "nombre": "Admin", "rol": "admin", "activo": True}])
    restaurants = _load_or_default('restaurants.json', [{"id": 1, "nombre": "Rest1", "admin_id": 1, "total_mesas": 10}])
    menus = _load_or_default('menus.json', [{"id": 1, "nombre": "Item1", "precio": 1000, "restaurante_id": 1}])
    orders = _load_or_default('orders.json', [])
    reservations = _load_or_default('reservations.json', [])

    if export:
        base.mkdir(parents=True, exist_ok=True)
        with open(base / 'users.json', 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

    return {
        "users": users,
        "restaurants": restaurants,
        "menus": menus,
        "orders": orders,
        "reservations": reservations,
    }


# ==================== FIXTURES DE DATOS ====================

@pytest.fixture(scope="session")
def test_data_dir():
    """Directorio de datos de prueba."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def generated_test_data():
    """
    Datos de prueba generados dinámicamente.
    Se regeneran una vez por sesión de tests.
    """
    return generate_all_test_data(export=False)


@pytest.fixture(scope="function")
def load_json_data(test_data_dir):
    """
    Carga datos JSON de los archivos en tests/data/
    """
    def _load(filename: str) -> list:
        file_path = test_data_dir / filename
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    return _load


@pytest.fixture(scope="function")
def users_data(load_json_data):
    """Carga usuarios de prueba."""
    return load_json_data("users.json")


@pytest.fixture(scope="function")
def restaurants_data(load_json_data):
    """Carga restaurantes de prueba."""
    return load_json_data("restaurants.json")


@pytest.fixture(scope="function")
def menus_data(load_json_data):
    """Carga menús de prueba."""
    return load_json_data("menus.json")


@pytest.fixture(scope="function")
def orders_data(load_json_data):
    """Carga órdenes de prueba."""
    return load_json_data("orders.json")


@pytest.fixture(scope="function")
def reservations_data(load_json_data):
    """Carga reservas de prueba."""
    return load_json_data("reservations.json")


# ==================== FIXTURES DE GENERACIÓN DINÁMICA ====================

@pytest.fixture(scope="function")
def random_user(generated_test_data):
    """Retorna un usuario aleatorio de los datos generados."""
    import random
    return random.choice(generated_test_data["users"])


@pytest.fixture(scope="function")
def random_restaurant(generated_test_data):
    """Retorna un restaurante aleatorio de los datos generados."""
    import random
    return random.choice(generated_test_data["restaurants"])


@pytest.fixture(scope="function")
def random_menu(generated_test_data):
    """Retorna un menú aleatorio de los datos generados."""
    import random
    return random.choice(generated_test_data["menus"])


@pytest.fixture(scope="function")
def random_order(generated_test_data):
    """Retorna una orden aleatoria de los datos generados."""
    import random
    return random.choice(generated_test_data["orders"])


@pytest.fixture(scope="function")
def random_reservation(generated_test_data):
    """Retorna una reserva aleatoria de los datos generados."""
    import random
    return random.choice(generated_test_data["reservations"])


# ==================== FIXTURES DE UTILIDADES ====================

@pytest.fixture
def api_headers():
    """Headers por defecto para requests a API."""
    return {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-token-mock"
    }


class TestDataFactory:
    """Factory para crear datos de prueba personalizados."""
    
    @staticmethod
    def create_user(**kwargs):
        """Crea un usuario personalizado."""
        user_id = kwargs.pop("id", 1)
        return DataGenerator.generate_user(user_id, **kwargs)
    
    @staticmethod
    def create_restaurant(**kwargs):
        """Crea un restaurante personalizado."""
        rest_id = kwargs.pop("id", 1)
        admin_id = kwargs.pop("admin_id", 1)
        restaurant = DataGenerator.generate_restaurant(rest_id, admin_id)
        restaurant.update(kwargs)
        return restaurant
    
    @staticmethod
    def create_menu(**kwargs):
        """Crea un menú personalizado."""
        menu_id = kwargs.pop("id", 1)
        rest_id = kwargs.pop("restaurante_id", 1)
        menu = DataGenerator.generate_menu(menu_id, rest_id)
        menu.update(kwargs)
        return menu
    
    @staticmethod
    def create_order(**kwargs):
        """Crea una orden personalizada."""
        order_id = kwargs.pop("id", 1)
        usuario_id = kwargs.pop("usuario_id", 1)
        rest_id = kwargs.pop("restaurante_id", 1)
        menu_ids = kwargs.pop("menu_ids", list(range(1, 11)))
        order = DataGenerator.generate_order(order_id, usuario_id, rest_id, menu_ids)
        order.update(kwargs)
        return order
    
    @staticmethod
    def create_reservation(**kwargs):
        """Crea una reserva personalizada."""
        res_id = kwargs.pop("id", 1)
        usuario_id = kwargs.pop("usuario_id", 1)
        rest_id = kwargs.pop("restaurante_id", 1)
        total_mesas = kwargs.pop("total_mesas", 20)
        reservation = DataGenerator.generate_reservation(res_id, usuario_id, rest_id, total_mesas)
        reservation.update(kwargs)
        return reservation


@pytest.fixture
def factory():
    """Factory para crear datos de prueba personalizados."""
    return TestDataFactory()


# ==================== CONFIGURACIÓN DE PYTEST ====================

def pytest_configure(config):
    """Configuración inicial de pytest."""
    # Agregar markers personalizados
    config.addinivalue_line(
        "markers", 
        "unit: marca tests unitarios"
    )
    config.addinivalue_line(
        "markers",
        "integration: marca tests de integración"
    )
    config.addinivalue_line(
        "markers",
        "slow: marca tests que son lentos"
    )
    config.addinivalue_line(
        "markers",
        "cache: marca tests que prueban caché"
    )
    config.addinivalue_line(
        "markers",
        "search: marca tests que prueban search service"
    )
