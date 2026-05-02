from sqlalchemy.orm import Session
from app.dao.base_dao import BaseDAO
from app.models.user import User, RoleEnum

class PostgreSQLUserDAO(BaseDAO):
    """
    Implementación postgres del dao de users. Siempre usamos basedao para definir la interfaz
    Todas las queries a la tabla users viven aqui lo podemos tomar como una capa de repository pero obviamente es el dao
    """
    #Conexion a la bd con sqlalchemy, ya implementado en el entregable anterior
    def __init__(self, session: Session):
        self.session = session

    # Queries de lectura

    #Busca usuario por id y retorna el primero
    def get_by_id(self, user_id: int) -> User | None:
        return self.session.query(User).filter(User.id == user_id).first()

    #Busca usuario por emiail y retorna el primero
    def get_by_email(self, email: str) -> User | None:
        return self.session.query(User).filter(User.email == email).first()

    #Metododo para listar a todos los usuarios que esten en la bd
    def get_all(self) -> list[User]:
        return self.session.query(User).all()

    #Verifica si ya existe algun admin en el sistema, mas que nada para el registro del primer usuario
    def get_first_admin(self) -> User | None:
        return self.session.query(User).filter(User.rol == RoleEnum.ADMIN).first()

    # Queries de escritura

    #Crea un usuario en la bd usando orm
    def create(self, data: dict) -> User:
    
        user = User(
            email=data["email"],
            nombre=data["nombre"],
            password_hash=data.get("password_hash", "cognito"), # Conexion con cognito
            rol=data.get("rol", RoleEnum.CLIENTE),
            activo=data.get("activo", True)
        )

        #Lo anadimos a la sesion, commit guarda en bd y refresh actualiza el objeto
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def update(self, user: User, data: dict) -> User:
        """
        Actualiza solo los campos recibidos en data.
        El service usa model_dump(exclude_unset=True) antes de llamar esto, osea solo legan los campos que cambian.
        """
        for field, value in data.items():
            setattr(user, field, value)
        self.session.commit()
        self.session.refresh(user)
        return user
    
    # Elimina un usuario de la bd, es delete fisico pero aun no se si quitarlo o dejarlo jaja
    def delete(self, user: User) -> User:
        self.session.delete(user)
        self.session.commit()
        return user

    # Soft delete mas sencillo evita problemas con cognito y es el que usamos actualmente
    def deactivate(self, user: User) -> User:
        user.activo = False
        self.session.commit()
        self.session.refresh(user)
        return user