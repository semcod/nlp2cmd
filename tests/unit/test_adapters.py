"""
Unit tests for NLP2CMD adapters.
"""

import pytest

from nlp2cmd.adapters import (
    SQLAdapter,
    ShellAdapter,
    DockerAdapter,
    KubernetesAdapter,
    SQLSafetyPolicy,
    ShellSafetyPolicy,
)


class TestSQLAdapter:
    """Tests for SQL adapter."""

    def test_simple_select(self):
        """Test simple SELECT generation."""
        adapter = SQLAdapter(dialect="postgresql")
        plan = {
            "intent": "select",
            "entities": {
                "table": "users",
                "columns": "*",
                "filters": [
                    {"field": "city", "operator": "=", "value": "Warsaw"}
                ],
            },
        }

        result = adapter.generate(plan)

        assert "SELECT *" in result
        assert "FROM users" in result
        assert "city = 'Warsaw'" in result

    def test_select_with_ordering(self):
        """Test SELECT with ORDER BY."""
        adapter = SQLAdapter(dialect="postgresql")
        plan = {
            "intent": "select",
            "entities": {
                "table": "products",
                "columns": ["name", "price"],
                "ordering": [{"field": "price", "direction": "DESC"}],
                "limit": 10,
            },
        }

        result = adapter.generate(plan)

        assert "ORDER BY price DESC" in result
        assert "LIMIT 10" in result

    def test_aggregate_query(self):
        """Test aggregate query generation."""
        adapter = SQLAdapter(dialect="postgresql")
        plan = {
            "intent": "aggregate",
            "entities": {
                "base_table": "orders",
                "aggregations": [
                    {"function": "COUNT", "field": "*", "alias": "total"}
                ],
                "grouping": ["status"],
            },
        }

        result = adapter.generate(plan)

        assert "COUNT(*) AS total" in result
        assert "GROUP BY status" in result

    def test_safety_blocks_delete(self):
        """Test that safety policy blocks DELETE."""
        policy = SQLSafetyPolicy(allow_delete=False)
        adapter = SQLAdapter(dialect="postgresql", safety_policy=policy)

        result = adapter.check_safety("DELETE FROM users WHERE id = 1;")

        assert not result["allowed"]
        assert "DELETE" in result["reason"]

    def test_safety_requires_where_on_update(self):
        """Test that safety policy requires WHERE on UPDATE."""
        policy = SQLSafetyPolicy(require_where_on_update=True)
        adapter = SQLAdapter(dialect="postgresql", safety_policy=policy)

        result = adapter.check_safety("UPDATE users SET active = false;")

        assert not result["allowed"]
        assert "WHERE" in result["reason"]

    def test_validate_syntax_balanced(self):
        """Test syntax validation for balanced parentheses."""
        adapter = SQLAdapter(dialect="postgresql")

        valid = adapter.validate_syntax("SELECT * FROM users WHERE (id = 1)")
        assert valid["valid"]

        invalid = adapter.validate_syntax("SELECT * FROM users WHERE (id = 1")
        assert not invalid["valid"]
        assert "parentheses" in invalid["errors"][0].lower()


class TestShellAdapter:
    """Tests for Shell adapter."""

    def test_file_search(self):
        """Test file search command generation."""
        adapter = ShellAdapter()
        plan = {
            "intent": "file_search",
            "entities": {
                "target": "files",
                "filters": [
                    {"attribute": "size", "operator": ">", "value": "100M"},
                    {"attribute": "mtime", "value": "7_days"},
                ],
            },
        }

        result = adapter.generate(plan)

        assert "find" in result
        assert "-size +100M" in result
        assert "-mtime -7" in result
        assert "-printf" in result
        assert "sort -nr" in result

    def test_process_monitoring(self):
        """Test process monitoring command."""
        adapter = ShellAdapter()
        plan = {
            "intent": "process_monitoring",
            "entities": {
                "metric": "memory",
                "limit": 5,
            },
        }

        result = adapter.generate(plan)

        assert "ps" in result
        assert "mem" in result

    def test_process_management_direct_ps(self):
        """Test direct ps request handling."""
        adapter = ShellAdapter()
        plan = {
            "intent": "process_management",
            "entities": {},
            "text": "ps aux",
        }

        result = adapter.generate(plan)

        assert result == "ps aux"

    def test_process_management_kill_pid(self):
        """Test process kill by PID."""
        adapter = ShellAdapter()
        plan = {
            "intent": "process_management",
            "entities": {
                "action": "kill",
                "pid": "123",
            },
            "text": "kill 123",
        }

        result = adapter.generate(plan)

        assert result == "kill -9 123"

    def test_process_management_start_service(self):
        """Test process start for a service."""
        adapter = ShellAdapter()
        plan = {
            "intent": "process_management",
            "entities": {
                "action": "start",
                "process_name": "nginx",
            },
            "text": "uruchom nginx",
        }

        result = adapter.generate(plan)

        assert result == "systemctl start nginx"

    def test_process_management_status_service(self):
        """Test status check for a service."""
        adapter = ShellAdapter()
        plan = {
            "intent": "process_management",
            "entities": {
                "action": "status usługi",
                "process_name": "nginx",
            },
            "text": "status usługi nginx",
        }

        result = adapter.generate(plan)

        assert result == "systemctl status nginx"

    def test_safety_blocks_dangerous(self):
        """Test that dangerous commands are blocked."""
        policy = ShellSafetyPolicy()
        adapter = ShellAdapter(safety_policy=policy)

        result = adapter.check_safety("rm -rf /")

        assert not result["allowed"]

    def test_safety_blocks_sudo(self):
        """Test that sudo is blocked by default."""
        policy = ShellSafetyPolicy(allow_sudo=False)
        adapter = ShellAdapter(safety_policy=policy)

        result = adapter.check_safety("sudo rm -rf /tmp/test")

        assert "requires_confirmation" in result or not result.get("allowed", True)

    def test_validate_syntax(self):
        """Test shell syntax validation."""
        adapter = ShellAdapter()

        valid = adapter.validate_syntax("echo 'hello world'")
        assert valid["valid"]

        invalid = adapter.validate_syntax("echo 'hello")
        assert not invalid["valid"]


class TestDockerAdapter:
    """Tests for Docker adapter."""

    def test_run_command(self):
        """Test docker run generation."""
        adapter = DockerAdapter()
        plan = {
            "intent": "container_run",
            "entities": {
                "image": "nginx",
                "name": "web",
                "ports": ["80:80"],
            },
        }

        result = adapter.generate(plan)

        assert "docker run" in result
        assert "nginx" in result
        assert "--name web" in result
        assert "-p 80:80" in result

    def test_compose_up(self):
        """Test docker-compose up generation."""
        adapter = DockerAdapter()
        plan = {
            "intent": "compose_up",
            "entities": {
                "detach": True,
                "build": True,
            },
        }

        result = adapter.generate(plan)

        assert "docker-compose" in result
        assert "up" in result
        assert "-d" in result
        assert "--build" in result

    def test_safety_blocks_privileged(self):
        """Test that privileged mode is blocked."""
        adapter = DockerAdapter()

        result = adapter.check_safety("docker run --privileged nginx")

        assert not result["allowed"]

    def test_adds_image_tag(self):
        """Test that missing image tag is warned."""
        adapter = DockerAdapter()

        result = adapter.validate_syntax("docker run nginx")

        assert any("tag" in w.lower() for w in result.get("warnings", []))


class TestKubernetesAdapter:
    """Tests for Kubernetes adapter."""

    def test_get_pods(self):
        """Test kubectl get pods generation."""
        adapter = KubernetesAdapter()
        plan = {
            "intent": "get",
            "entities": {
                "resource_type": "pods",
                "namespace": "default",
            },
        }

        result = adapter.generate(plan)

        assert "kubectl get pods" in result
        assert "-n default" in result

    def test_scale_deployment(self):
        """Test kubectl scale generation."""
        adapter = KubernetesAdapter()
        plan = {
            "intent": "scale",
            "entities": {
                "resource_name": "nginx",
                "replica_count": 5,
            },
        }

        result = adapter.generate(plan)

        assert "kubectl scale" in result
        assert "--replicas=5" in result
        assert "nginx" in result

    def test_exec_command(self):
        """Test kubectl exec generation."""
        adapter = KubernetesAdapter()
        plan = {
            "intent": "exec",
            "entities": {
                "pod_name": "web-pod",
                "command": "/bin/bash",
            },
        }

        result = adapter.generate(plan)

        assert "kubectl exec" in result
        assert "-it" in result
        assert "web-pod" in result

    def test_safety_blocks_system_namespace(self):
        """Test that system namespaces are blocked."""
        adapter = KubernetesAdapter()

        result = adapter.check_safety("kubectl delete pod test -n kube-system")

        # Should warn about system namespace
        assert not result.get("allowed", True) or "blocked" in str(result).lower()


class TestAdapterIntegration:
    """Integration tests for adapters."""

    def test_sql_full_flow(self):
        """Test complete SQL transformation flow."""
        adapter = SQLAdapter(
            dialect="postgresql",
            schema_context={"tables": ["users", "orders"]},
        )

        # Generate
        plan = {
            "intent": "select",
            "entities": {
                "table": "users",
                "filters": [{"field": "active", "operator": "=", "value": True}],
            },
        }
        command = adapter.generate(plan)

        # Validate
        validation = adapter.validate_syntax(command)
        assert validation["valid"]

        # Safety check
        safety = adapter.check_safety(command)
        assert safety["allowed"]

    def test_shell_full_flow(self):
        """Test complete Shell transformation flow."""
        adapter = ShellAdapter(
            environment_context={"os": "linux", "distro": "ubuntu"},
        )

        plan = {
            "intent": "file_search",
            "entities": {
                "target": "files",
                "filters": [{"attribute": "name", "value": "*.py"}],
            },
        }
        command = adapter.generate(plan)

        validation = adapter.validate_syntax(command)
        assert validation["valid"]

        safety = adapter.check_safety(command)
        assert safety["allowed"]


class TestBrowserAdapterTransformIR:
    """Regression tests for BrowserAdapter + transform_ir integration."""

    def test_transform_ir_dsl_kind_is_dom(self):
        """BrowserAdapter.transform_ir must produce dsl_kind='dom', not 'shell'.

        Regression: BrowserAdapter.DSL_NAME='browser' was not mapped to 'dom'
        in core_transform.py, causing JSON DSL to be executed as a shell command.
        """
        from nlp2cmd.adapters.browser import BrowserAdapter
        from nlp2cmd.core.core_transform import NLP2CMD

        adapter = BrowserAdapter()
        nlp = NLP2CMD(adapter=adapter)
        ir = nlp.transform_ir("otwórz https://example.com/contact i wypełnij formularz i wyślij")

        assert ir.dsl_kind == "dom", f"Expected dsl_kind='dom', got '{ir.dsl_kind}'"
        assert ir.confidence > 0, "Confidence should be positive"

        import json
        payload = json.loads(ir.dsl)
        assert payload.get("dsl") == "dom_dql.v1"
        actions = [a.get("action") for a in payload.get("actions", [])]
        assert "goto" in actions
        assert "fill_form" in actions
        assert "submit" in actions

    def test_transform_ir_simple_navigate(self):
        """Simple navigation should also produce dsl_kind='dom'."""
        from nlp2cmd.adapters.browser import BrowserAdapter
        from nlp2cmd.core.core_transform import NLP2CMD

        adapter = BrowserAdapter()
        nlp = NLP2CMD(adapter=adapter)
        ir = nlp.transform_ir("otwórz https://google.com")

        assert ir.dsl_kind == "dom"
        import json
        payload = json.loads(ir.dsl)
        assert payload.get("dsl") == "dom_dql.v1"
        assert "google.com" in payload.get("url", "")
