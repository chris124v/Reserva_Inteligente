"""
Pruebas unitarias básicas de validaciones (esquemas Pydantic).

Archivo simple para cerrar la parte de unit tests: valida que los modelos
de `app.schemas.user` aplican las restricciones mínimas.
"""

import pytest
from pydantic import ValidationError
from app.schemas.user import UserCreate


def test_user_create_valid():
	"""Creación válida de usuario con campos mínimos."""
	u = UserCreate(email="user@example.com", nombre="Usuario", password="strongpass")
	assert u.email == "user@example.com"
	assert u.nombre == "Usuario"


def test_user_create_invalid_short_password():
	"""Password demasiado corto debe lanzar ValidationError."""
	with pytest.raises(ValidationError):
		UserCreate(email="a@b.com", nombre="X", password="short")

