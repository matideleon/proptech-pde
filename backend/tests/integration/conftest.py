"""
Fixtures de integración: DB de testing, cliente HTTP y usuarios.

Estas fixtures requieren PostgreSQL disponible. Si no lo está, los tests
de integración se omiten automáticamente (skip) en lugar de fallar.
"""
import pytest
import pytest_asyncio

# Importes pesados aislados aquí — no afectan a los tests unitarios.
try:
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    from app.core.config import settings
    from app.core.security import hash_password
    from app.db.database import Base, get_db
    from app.main import app
    from app.models.user import User, UserRole

    _INTEGRATION_AVAILABLE = True
except Exception as exc:  # noqa: BLE001
    _INTEGRATION_AVAILABLE = False
    _IMPORT_ERROR = str(exc)


pytestmark = pytest.mark.skipif(
    not _INTEGRATION_AVAILABLE,
    reason="Stack de integración no disponible (falta DB/deps).",
)


if _INTEGRATION_AVAILABLE:
    TEST_DB_URL = settings.DATABASE_URL.replace("proptech_pde", "proptech_pde_test")
    engine = create_async_engine(TEST_DB_URL, echo=False)
    TestSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    @pytest_asyncio.fixture(scope="function")
    async def db() -> AsyncSession:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with TestSessionLocal() as session:
            yield session
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @pytest_asyncio.fixture(scope="function")
    async def client(db):
        app.dependency_overrides[get_db] = lambda: db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
        app.dependency_overrides.clear()

    @pytest_asyncio.fixture
    async def admin_user(db) -> "User":
        user = User(
            email="admin@test.com",
            full_name="Test Admin",
            hashed_password=hash_password("testpass123"),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def admin_token(client, admin_user) -> str:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "testpass123"},
        )
        return response.json()["access_token"]
