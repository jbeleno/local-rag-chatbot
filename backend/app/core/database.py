"""
Configuración de base de datos con SQLAlchemy.
"""
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy.pool import StaticPool, QueuePool
from typing import Generator

from app.core.config import settings

logger = logging.getLogger(__name__)

# Base para modelos (SQLAlchemy 2.0 style)
class Base(DeclarativeBase):
    pass

# Variable global para el engine
engine = None
SessionLocal = None


def get_database_url() -> str:
    """
    Obtener la URL de conexión a la base de datos.
    
    Returns:
        URL de conexión SQLAlchemy
    """
    if settings.DATABASE_URL and (settings.USE_POSTGRES or settings.DATABASE_URL.startswith("postgresql")):
        # PostgreSQL - usar la URL directamente
        return str(settings.DATABASE_URL)
    else:
        # SQLite - usar ruta relativa
        db_path = settings.MEMORY_DB_PATH
        # Asegurar que la ruta sea absoluta para SQLite
        from pathlib import Path
        if not Path(db_path).is_absolute():
            # Si es relativa, hacerla relativa al directorio del proyecto
            db_path = str(Path(__file__).parent.parent.parent / db_path)
        return f"sqlite:///{db_path}"


def init_database():
    """
    Inicializar la conexión a la base de datos.
    """
    global engine, SessionLocal
    
    database_url = get_database_url()
    is_sqlite = database_url.startswith("sqlite")
    
    # Configuración del engine según el tipo de base de datos
    if is_sqlite:
        # SQLite: usar StaticPool para mejor compatibilidad
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False  # Cambiar a True para ver queries SQL
        )
        logger.info(f"Base de datos SQLite inicializada: {database_url}")
    else:
        # PostgreSQL: usar QueuePool con configuración
        engine = create_engine(
            database_url,
            pool_size=settings.POSTGRES_POOL_MIN_CONN,
            max_overflow=settings.POSTGRES_POOL_MAX_CONN - settings.POSTGRES_POOL_MIN_CONN,
            pool_pre_ping=True,  # Verificar conexiones antes de usarlas
            echo=False  # Cambiar a True para ver queries SQL
        )
        masked_url = database_url.split("@")[-1] if "@" in database_url else "postgres"
        logger.info(f"Base de datos PostgreSQL inicializada: {masked_url}")
    
    # Crear sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)
    logger.info("Tablas de base de datos creadas/verificadas")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency para obtener sesión de base de datos.
    Útil para FastAPI dependency injection.
    
    Yields:
        Sesión de SQLAlchemy
    """
    if SessionLocal is None:
        raise RuntimeError("Base de datos no inicializada. Llama a init_database() primero.")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Importar modelos para que se registren con Base
from app.models import database_models, document_models  # noqa: F401

# Inicializar al importar el módulo
init_database()

