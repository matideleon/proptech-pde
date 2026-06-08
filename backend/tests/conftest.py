"""
Configuración raíz de pytest.

Las fixtures pesadas (DB, HTTP client, app) viven en
tests/integration/conftest.py para que los tests unitarios puros
(p. ej. el normalizer) puedan ejecutarse sin levantar todo el stack.
"""
import asyncio

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Event loop compartido para toda la sesión de tests async."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
