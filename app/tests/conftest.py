"""
Configuración global de fixtures para los tests.
Este archivo es automáticamente descubierto y usado por pytest.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import FastAPI, Request, Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.database.connection import Base
from app.database.session import get_db


# ==================== BASE DE DATOS ====================

@pytest.fixture(scope="session")
def test_db_engine():
    """
    Crea un motor de base de datos en memoria para las pruebas.
    Se usa SQLite en memoria para velocidad y simplicidad.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db(test_db_engine):
    """
    Crea una sesión de base de datos para cada test.
    Se usa function scope para aislar cada test.
    """
    connection = test_db_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


# ==================== CLIENTE HTTP ====================

@pytest.fixture
def client(test_db):
    """
    Crea un cliente HTTP TestClient para hacer requests a la API.
    Inyecta la sesión de prueba en el override de get_db y mockea verify_jwt.
    """
    from app.main import app
    from app.auth.middleware import verify_jwt
    from fastapi import HTTPException
    
    # Create mock that respects Authorization header presence
    async def mock_verify_jwt_func(request: Request, db: Session = Depends(get_db)):
        # Check if Authorization header is present
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="No token provided")

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid Authorization header")

        token = parts[1]

        # For tests, token "test-token" devuelve el primer usuario creado
        from app.models.user import User
        user = db.query(User).order_by(User.id).first()
        if not user:
            # En tests sin usuario creado, devolvemos un usuario mock que exista en el flujo
            return {
                "sub": "1",
                "email": "test@example.com",
                "cognito:username": "testuser"
            }

        return {
            "sub": str(user.id),
            "email": user.email,
            "cognito:username": user.nombre
        }
    
    def override_get_db():
        yield test_db
    
    # Override both dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[verify_jwt] = mock_verify_jwt_func
    
    client = TestClient(app)
    yield client
    
    app.dependency_overrides.clear()


# ==================== AUTENTICACIÓN ====================

@pytest.fixture
def mock_settings():
    """
    Mock de las variables de configuración.
    """
    with patch("app.config.settings") as m:
        m.AWS_REGION = "us-east-2"
        m.COGNITO_USER_POOL_ID = "us-east-2_test123"
        m.COGNITO_CLIENT_ID = "test-client-id"
        m.COGNITO_CLIENT_SECRET = "test-client-secret"
        yield m


@pytest.fixture
def mock_cognito_client(mock_settings):
    """
    Mock del cliente de Cognito.
    """
    with patch("app.auth.cognito.CognitoClient") as m:
        mock_instance = MagicMock()
        m.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def valid_token():
    """
    Token JWT válido para usar en los tests.
    """
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.test-signature"


@pytest.fixture
def auth_headers(valid_token):
    """
    Headers de autorización con token válido.
    """
    return {"Authorization": f"Bearer {valid_token}"}


@pytest.fixture
def mock_verify_jwt():
    """
    Mock de la función verify_jwt.
    Retorna un usuario de prueba.
    """
    def _mock_verify(token: str):
        return {"sub": "1", "email": "test@example.com"}
    
    with patch("app.auth.middleware.verify_jwt") as m:
        m.return_value = {"sub": "1", "email": "test@example.com"}
        yield m


# ==================== DATOS DE PRUEBA ====================

@pytest.fixture
def test_user_data():
    """
    Datos de un usuario de prueba.
    """
    return {
        "email": "test@example.com",
        "nombre": "Test User",
        "password": "TestPassword123!",
        "rol": "cliente"
    }


@pytest.fixture
def test_restaurant_data():
    """
    Datos de un restaurante de prueba.
    """
    return {
        "nombre": "Test Restaurant",
        "descripcion": "Un restaurante de prueba",
        "direccion": "Calle Test 123",
        "telefono": "555-1234",
        "email": "restaurant@test.com",
        "hora_apertura": "09:00",
        "hora_cierre": "22:00",
        "total_mesas": 10
    }


@pytest.fixture
def test_menu_data():
    """
    Datos de un menú de prueba.
    """
    return {
        "nombre": "Hamburguesa",
        "descripcion": "Deliciosa hamburguesa",
        "precio": 15.50,
        "disponible": True
    }


@pytest.fixture
def test_reservation_data():
    """
    Datos de una reserva de prueba.
    """
    from datetime import date, time, timedelta
    tomorrow = date.today() + timedelta(days=1)
    
    return {
        "restaurante_id": 1,
        "fecha": tomorrow.isoformat(),
        "hora": "19:30",
        "cantidad_personas": 4,
        "notas": "Mesa cerca de la ventana"
    }


@pytest.fixture
def test_order_data():
    """
    Datos de un pedido de prueba.
    """
    return {
        "restaurante_id": 1,
        "items": [
            {"menu_id": 1, "cantidad": 2},
            {"menu_id": 2, "cantidad": 1}
        ],
        "tipo_entrega": "en_restaurante",
        "notas": "Sin picante"
    }


# ==================== HELPERS ====================

@pytest.fixture
def create_test_data(test_db):
    """
    Helper para crear datos de prueba en la BD.
    """
    def _create_user(email="test@example.com", nombre="Test User", rol="cliente"):
        from app.models.user import User, RoleEnum
        user = User(
            email=email,
            nombre=nombre,
            password_hash="hashed_password",
            rol=RoleEnum[rol.upper()] if isinstance(rol, str) else rol,
            activo=True
        )
        test_db.add(user)
        test_db.commit()
        return user
    
    def _create_restaurant(nombre="Test Restaurant", admin_id=1):
        from app.models.restaurant import Restaurant
        from datetime import time
        restaurant = Restaurant(
            nombre=nombre,
            descripcion="Descripción",
            direccion="Calle Test 123",
            telefono="555-1234",
            email=f"{nombre.lower().replace(' ', '')}@test.com",
            admin_id=admin_id,
            hora_apertura=time(9, 0),
            hora_cierre=time(22, 0),
            total_mesas=10
        )
        test_db.add(restaurant)
        test_db.commit()
        return restaurant
    
    return {
        "create_user": _create_user,
        "create_restaurant": _create_restaurant
    }
