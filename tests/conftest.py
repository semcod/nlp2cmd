"""
Pytest configuration and fixtures for NLP2CMD tests.
"""

import pytest
import sys
from pathlib import Path
import tempfile
import asyncio
import inspect

_repo_root = Path(__file__).resolve().parents[1]
_src_path = _repo_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))


@pytest.fixture(scope="session")
def sql_adapter():
    """Provide a configured SQL adapter."""
    from nlp2cmd.adapters import SQLAdapter

    return SQLAdapter(
        dialect="postgresql",
        schema_context={
            "tables": ["users", "orders", "products"],
            "relations": {
                "orders.user_id": "users.id",
                "orders.product_id": "products.id",
            },
        },
    )


@pytest.fixture(scope="session")
def sql_adapter_strict():
    """Provide a SQL adapter with strict safety policy."""
    from nlp2cmd.adapters import SQLAdapter, SQLSafetyPolicy

    policy = SQLSafetyPolicy(
        allow_delete=False,
        allow_truncate=False,
        allow_drop=False,
        require_where_on_update=True,
        require_where_on_delete=True,
    )
    return SQLAdapter(dialect="postgresql", safety_policy=policy)


@pytest.fixture(scope="session")
def shell_adapter():
    """Provide a configured Shell adapter."""
    from nlp2cmd.adapters import ShellAdapter

    return ShellAdapter(
        shell_type="bash",
        environment_context={
            "os": "linux",
            "distro": "ubuntu",
            "available_tools": ["git", "docker", "kubectl"],
        },
    )


@pytest.fixture(scope="session")
def shell_adapter_strict():
    """Provide a Shell adapter with strict safety policy."""
    from nlp2cmd.adapters import ShellAdapter, ShellSafetyPolicy

    policy = ShellSafetyPolicy(
        allow_sudo=False,
        sandbox_mode=True,
    )
    return ShellAdapter(safety_policy=policy)


@pytest.fixture(scope="session")
def docker_adapter():
    """Provide a configured Docker adapter."""
    from nlp2cmd.adapters import DockerAdapter

    return DockerAdapter()


@pytest.fixture(scope="session")
def kubernetes_adapter():
    """Provide a configured Kubernetes adapter."""
    from nlp2cmd.adapters import KubernetesAdapter

    return KubernetesAdapter()


@pytest.fixture
def nlp2cmd_sql(sql_adapter):
    """Provide NLP2CMD instance with SQL adapter."""
    from nlp2cmd import NLP2CMD

    return NLP2CMD(adapter=sql_adapter)


@pytest.fixture
def nlp2cmd_shell(shell_adapter):
    """Provide NLP2CMD instance with Shell adapter."""
    from nlp2cmd import NLP2CMD

    return NLP2CMD(adapter=shell_adapter)


@pytest.fixture(scope="session")
def schema_registry():
    """Provide a SchemaRegistry instance."""
    from nlp2cmd.schemas import SchemaRegistry

    return SchemaRegistry()


@pytest.fixture(scope="session")
def feedback_analyzer():
    """Provide a FeedbackAnalyzer instance."""
    from nlp2cmd.feedback import FeedbackAnalyzer

    return FeedbackAnalyzer()


@pytest.fixture(scope="session")
def environment_analyzer():
    """Provide an EnvironmentAnalyzer instance."""
    from nlp2cmd.environment import EnvironmentAnalyzer

    return EnvironmentAnalyzer()


def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: mark test to run in an asyncio event loop")
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "requires_docker: marks tests that require Docker")


@pytest.fixture(scope="session")
def _session_event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.run_until_complete(loop.shutdown_asyncgens())
        asyncio.set_event_loop(None)
        loop.close()


@pytest.fixture(autouse=True)
def _default_event_loop(_session_event_loop):
    """Expose the shared event loop to legacy tests that call get_event_loop()."""
    asyncio.set_event_loop(_session_event_loop)
    try:
        yield
    finally:
        asyncio.set_event_loop(None)


def pytest_pyfunc_call(pyfuncitem):
    testfunction = pyfuncitem.obj
    if inspect.iscoroutinefunction(testfunction):
        funcargs = {arg: pyfuncitem.funcargs[arg] for arg in pyfuncitem._fixtureinfo.argnames}
        loop = asyncio.get_event_loop()
        loop.run_until_complete(testfunction(**funcargs))
        pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        return True
    return None


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_dockerfile(temp_dir):
    """Create a sample Dockerfile for testing."""
    content = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py"]
"""
    path = temp_dir / "Dockerfile"
    path.write_text(content)
    return path


@pytest.fixture
def sample_compose(temp_dir):
    """Create a sample docker-compose.yml for testing."""
    content = """version: "3.8"
services:
  web:
    build: .
    ports:
      - "8080:80"
    depends_on:
      - db
  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: secret
    volumes:
      - db_data:/var/lib/postgresql/data

volumes:
  db_data:
"""
    path = temp_dir / "docker-compose.yml"
    path.write_text(content)
    return path


@pytest.fixture
def sample_env(temp_dir):
    """Create a sample .env file for testing."""
    content = """# Database configuration
DATABASE_URL=postgresql://localhost/mydb
DATABASE_USER=admin

# API Keys
API_KEY="super-secret-key"
DEBUG=true
"""
    path = temp_dir / ".env"
    path.write_text(content)
    return path


@pytest.fixture
def sample_k8s_deployment(temp_dir):
    """Create a sample Kubernetes deployment for testing."""
    content = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  labels:
    app: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: web
          image: nginx:1.21
          ports:
            - containerPort: 80
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "200m"
"""
    path = temp_dir / "deployment.yaml"
    path.write_text(content)
    return path


# Test data fixtures
@pytest.fixture
def sql_test_plans():
    """Provide sample SQL execution plans."""
    return [
        {
            "intent": "select",
            "entities": {
                "table": "users",
                "columns": "*",
            },
        },
        {
            "intent": "select",
            "entities": {
                "table": "users",
                "columns": ["id", "name", "email"],
                "filters": [
                    {"field": "active", "operator": "=", "value": True}
                ],
                "ordering": [{"field": "created_at", "direction": "DESC"}],
                "limit": 10,
            },
        },
        {
            "intent": "aggregate",
            "entities": {
                "base_table": "orders",
                "aggregations": [
                    {"function": "COUNT", "field": "*", "alias": "total"}
                ],
                "grouping": ["status"],
            },
        },
    ]


@pytest.fixture
def shell_test_plans():
    """Provide sample Shell execution plans."""
    return [
        {
            "intent": "file_search",
            "entities": {
                "target": "files",
                "filters": [
                    {"attribute": "size", "operator": ">", "value": "100M"}
                ],
            },
        },
        {
            "intent": "process_monitoring",
            "entities": {
                "metric": "memory",
                "limit": 10,
            },
        },
    ]


