import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database
    DATABASE_USER = os.getenv("DATABASE_USER")
    DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
    DATABASE_HOST = os.getenv("DATABASE_HOST")
    DATABASE_PORT = os.getenv("DATABASE_PORT")
    DATABASE_NAME = os.getenv("DATABASE_NAME")
    
    # AWS Cognito
    # Support both legacy and explicit Cognito env var names.
    AWS_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_COGNITO_REGION")
    COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID") or os.getenv("AWS_COGNITO_USER_POOL_ID")
    COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID") or os.getenv("AWS_COGNITO_CLIENT_ID")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    COGNITO_CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET")
    
    # API
    SECRET_KEY = os.getenv("SECRET_KEY", "tu-clave-secreta-aqui")
    ALGORITHM = "HS256"

    # Auth / Roles
    # Si se define, se requerirá este código para registrarse como admin.
    # Si NO se define, se permite bootstrap: el primer admin puede crearse solo si
    # aún no existe ningún usuario admin en la BD.
    ADMIN_REGISTRATION_CODE = os.getenv("ADMIN_REGISTRATION_CODE")

    # Código adicional para operaciones sensibles (gestión de usuarios).
    # Recomendación: usarlo solo en requests de admins autorizados.
    MASTER_ADMIN_CODE = os.getenv("MASTER_ADMIN_CODE")

settings = Settings()