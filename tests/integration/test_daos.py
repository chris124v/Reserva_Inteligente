"""
Integration tests para DAOs (PostgreSQL y MongoDB).
Pruebas esenciales del patrón Factory y operaciones CRUD en ambas bases de datos.

Categoría: INTEGRACIÓN
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from app.dao.factory import DAOFactory


# Factory retorna PostgreSQL DAO cuando DATABASE_TYPE es 'postgresql'
def test_factory_returns_postgresql_user_dao(monkeypatch):
    mock_session = Mock()
    
    from app.dao.factory import DAOFactory
    dao = DAOFactory.get_user_dao("postgresql", mock_session)
    
    assert dao is not None
    assert hasattr(dao, 'session')
    assert dao.session == mock_session


# Factory retorna MongoDB DAO cuando DATABASE_TYPE es 'mongodb'
def test_factory_returns_mongodb_user_dao(monkeypatch):
    mock_db = Mock()
    mock_db.__getitem__ = Mock(return_value=Mock())
    
    with patch("app.database.mongo.get_mongo_db", return_value=mock_db):
        from app.dao.factory import DAOFactory
        dao = DAOFactory.get_user_dao("mongodb", None)
        
        assert dao is not None
        assert hasattr(dao, 'collection')


# PostgreSQL create usuario con datos válidos
def test_postgresql_user_create_success(monkeypatch):
    mock_session = Mock()
    mock_user = Mock()
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_session.query.return_value.filter.return_value.first.return_value = None
    mock_session.add = Mock()
    mock_session.commit = Mock()
    mock_session.refresh = Mock(side_effect=lambda u: setattr(u, 'id', 1))
    
    from app.dao.postgresql.user_dao import PostgreSQLUserDAO
    dao = PostgreSQLUserDAO(mock_session)
    
    result = dao.create({
        "email": "newuser@test.com",
        "nombre": "Test User",
        "password_hash": "hashed_pass",
        "rol": "cliente"
    })
    
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


# MongoDB create usuario con ID autoincremental
def test_mongodb_user_create_success(monkeypatch):
    mock_collection = Mock()
    mock_collection.find_one.return_value = {"id": 5}
    mock_collection.insert_one = Mock()
    
    with patch("app.database.mongo.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        
        from app.dao.factory import DAOFactory
        dao = DAOFactory.get_user_dao("mongodb", None)
        
        result = dao.create({
            "email": "mongo@test.com",
            "nombre": "Mongo User",
            "password_hash": "hash",
            "rol": "cliente"
        })
        
        mock_collection.insert_one.assert_called_once()
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["id"] == 6  # ID autoincremental


# PostgreSQL get_by_id retorna usuario existente
def test_postgresql_user_get_by_id_success(monkeypatch):
    mock_session = Mock()
    mock_user = Mock()
    mock_user.id = 1
    mock_user.email = "found@test.com"
    mock_session.query.return_value.filter.return_value.first.return_value = mock_user
    
    from app.dao.postgresql.user_dao import PostgreSQLUserDAO
    dao = PostgreSQLUserDAO(mock_session)
    
    result = dao.get_by_id(1)
    
    assert result == mock_user
    mock_session.query.assert_called_once()


# MongoDB get_by_id retorna usuario existente
def test_mongodb_user_get_by_id_success(monkeypatch):
    mock_collection = Mock()
    mock_doc = {"id": 1, "email": "mongo@test.com", "nombre": "User", "rol": "cliente", "password_hash": "hash", "activo": True}
    mock_collection.find_one.return_value = mock_doc
    
    with patch("app.database.mongo.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db
        
        from app.dao.factory import DAOFactory
        dao = DAOFactory.get_user_dao("mongodb", None)
        
        result = dao.get_by_id(1)
        
        mock_collection.find_one.assert_called_once_with({"id": 1})
