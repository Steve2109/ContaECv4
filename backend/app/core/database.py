"""
ContaEC - Configuración de la base de datos
Soporte asíncrono para PostgreSQL (asyncpg)
"""
from datetime import datetime
from typing import AsyncGenerator
from uuid import uuid4

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

# Convención de nombres para restricciones (compatible con Alembic)
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """Clase base declarativa para todos los modelos SQLAlchemy"""
    metadata = metadata


# Configuración del engine asíncrono - PostgreSQL
settings = get_settings()

engine = create_async_engine(
    settings.database_url_async,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)


# Fábrica de sesiones asíncronas
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia de FastAPI que proporciona una sesión de base de datos asíncrona.
    Utiliza el patrón `async with` para garantizar el cierre de la sesión.

    NOTA ARQUITECTURAL: Este generador realiza un commit implícito al finalizar
    exitosamente la petición. Esto es un acoplamiento que debe ser refactorizado
    en el futuro: los endpoints deberían llamar a `await db.commit()` explícitamente.

    Si se elimina el commit automático, todos los endpoints de escritura que solo
    llaman a `await db.flush()` dejarán de persistir datos silenciosamente.
    Hay ~218 instancias de `await db.flush()` sin `await db.commit()` en los endpoints.

    Uso:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            # TODO: Remove implicit commit - requires auditing ~218 flush()-only endpoints
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        # session.close() is handled by async with context manager


async def _ensure_new_columns(conn) -> None:
    """
    Migraciones ligeras e idempotentes para columnas añadidas al modelo
    sin un sistema de migraciones formal (no hay Alembic en este proyecto).

    create_all NO agrega columnas nuevas a tablas existentes, por lo que
    las columnas agregadas posteriormente deben crearse con ALTER TABLE
    (solo PostgreSQL en producción; SQLite se omite).
    """
    dialect = conn.dialect.name
    if dialect != "postgresql":
        return

    from sqlalchemy import text

    statements = [
        # Usuarios: contraseña temporal pendiente de cambio (recuperación de contraseña)
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE",
        # Usuarios: sub-cuentas (cuentas creadas por otro usuario con acceso limitado)
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS parent_user_id UUID",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_subaccount BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS allowed_modules TEXT",
        # Cargas familiares: porcentaje y tipo de discapacidad
        "ALTER TABLE cargas_familiares ADD COLUMN IF NOT EXISTS porcentaje_discapacidad INTEGER",
        "ALTER TABLE cargas_familiares ADD COLUMN IF NOT EXISTS tipo_discapacidad VARCHAR(50)",
    ]
    for stmt in statements:
        await conn.execute(text(stmt))


async def init_db() -> None:
    """
    Inicializa la base de datos creando todas las tablas.
    Se debe llamar al iniciar la aplicación.
    
    Para PostgreSQL en producción, se recomienda usar Alembic
    para migraciones en lugar de create_all.
    """
    async with engine.begin() as conn:
        # Importar todos los modelos para que Base.metadata los conozca
        import app.models  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)
        await _ensure_new_columns(conn)


async def close_db() -> None:
    """
    Cierra la conexión a la base de datos.
    Se debe llamar al detener la aplicación.
    """
    await engine.dispose()
