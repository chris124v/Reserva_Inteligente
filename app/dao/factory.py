"""
factory es el patron que decide que implementacion de dao usar (osea las bds)
basado en una variable de entorno que es databasetype
"""

from app.dao.base_dao import BaseDAO


class DAOFactory:
    """
    Factory que produce daos basado en el tipo de bd, la clase no se instancia
    solo usamos metodos estaticos.
    """

    _DAO_MAPPING = {
        "postgresql": {
            "user": "app.dao.postgresql.user_dao.PostgreSQLUserDAO",
            "restaurant": "app.dao.postgresql.restaurant_dao.PostgreSQLRestaurantDAO",
            "menu": "app.dao.postgresql.menu_dao.PostgreSQLMenuDAO",
            "reservation": "app.dao.postgresql.reservation_dao.PostgreSQLReservationDAO",
            "order": "app.dao.postgresql.order_dao.PostgreSQLOrderDAO",
        },
        "mongodb": {
            "user": "app.dao.mongodb.user_dao.MongoDBUserDAO",
            "restaurant": "app.dao.mongodb.restaurant_dao.MongoDBRestaurantDAO",
            "menu": "app.dao.mongodb.menu_dao.MongoDBMenuDAO",
            "reservation": "app.dao.mongodb.reservation_dao.MongoDBReservationDAO",
            "order": "app.dao.mongodb.order_dao.MongoDBOrderDAO",
        }
    }

    @staticmethod
    def _resolve_connection(database_type: str, connection):
        """
        aqui postgres recibe la sesion de sqlalcemy directamente.
        mongo ignora la sesion  y usa get_mongo_db() propio
        """
        if database_type == "mongodb":
            from app.database.mongo import get_mongo_db
            return get_mongo_db()
        return connection

    @staticmethod
    def _get_dao(dao_type: str, database_type: str, connection) -> BaseDAO:
        if database_type not in DAOFactory._DAO_MAPPING:
            raise ValueError(
                f"Base de datos no soportada: {database_type}. "
                f"Opciones disponibles: {list(DAOFactory._DAO_MAPPING.keys())}"
            )

        resolved_connection = DAOFactory._resolve_connection(database_type, connection)

        dao_path = DAOFactory._DAO_MAPPING[database_type][dao_type]
        module_path, class_name = dao_path.rsplit(".", 1)

        module = __import__(module_path, fromlist=[class_name])
        dao_class = getattr(module, class_name)

        return dao_class(resolved_connection)

    @staticmethod
    def get_user_dao(database_type: str, connection) -> BaseDAO:
        return DAOFactory._get_dao("user", database_type, connection)

    @staticmethod
    def get_restaurant_dao(database_type: str, connection) -> BaseDAO:
        return DAOFactory._get_dao("restaurant", database_type, connection)

    @staticmethod
    def get_menu_dao(database_type: str, connection) -> BaseDAO:
        return DAOFactory._get_dao("menu", database_type, connection)

    @staticmethod
    def get_reservation_dao(database_type: str, connection) -> BaseDAO:
        return DAOFactory._get_dao("reservation", database_type, connection)

    @staticmethod
    def get_order_dao(database_type: str, connection) -> BaseDAO:
        return DAOFactory._get_dao("order", database_type, connection)
    