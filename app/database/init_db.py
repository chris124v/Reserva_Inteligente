from app.database.connection import Base, engine
import app.models  # noqa: F401  # Ensure all models are registered in Base metadata.


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database tables created/verified successfully.")
