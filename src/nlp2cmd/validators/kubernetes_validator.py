"""KubernetesValidator - extracted from __init__.py."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
import re
from nlp2cmd.validators.base_validator import BaseValidator
from nlp2cmd.validators.validation_result import ValidationResult

class KubernetesValidator(BaseValidator):
    """Kubernetes command and manifest validator."""

    BLOCKED_NAMESPACES = ["kube-system", "kube-public", "kube-node-lease"]

    def __init__(self, allowed_namespaces: Optional[list[str]] = None):
        self.allowed_namespaces = allowed_namespaces

    def validate(self, content: str) -> ValidationResult:
        """Validate kubectl command."""
        errors = []
        warnings = []
        suggestions = []

        content_stripped = (content or "").strip()
        content_lower = content_stripped.lower()

        is_kubectl_cmd = content_lower.startswith("kubectl ")
        is_manifest = (
            "\n" in content_stripped
            and re.search(r"^\s*apiVersion\s*:", content_stripped, flags=re.IGNORECASE | re.MULTILINE) is not None
            and re.search(r"^\s*kind\s*:", content_stripped, flags=re.IGNORECASE | re.MULTILINE) is not None
        )
        if not is_kubectl_cmd and not is_manifest:
            return ValidationResult(
                is_valid=False,
                errors=["Not a kubectl command"],
                warnings=[],
                suggestions=["Prefix the command with 'kubectl' or provide a Kubernetes YAML manifest"],
            )

        tokens = content_stripped.split()
        tokens_lower = [t.lower() for t in tokens]

        is_delete = len(tokens_lower) >= 2 and tokens_lower[1] == "delete"
        is_get = len(tokens_lower) >= 2 and tokens_lower[1] == "get"
        is_logs = len(tokens_lower) >= 2 and tokens_lower[1] == "logs"
        is_scale = len(tokens_lower) >= 2 and tokens_lower[1] == "scale"
        is_port_forward = len(tokens_lower) >= 2 and tokens_lower[1] in {"port-forward", "portforward"}

        # Extract namespace if present
        namespace: Optional[str] = None
        for i, t in enumerate(tokens_lower):
            if t in {"-n", "--namespace"} and i + 1 < len(tokens_lower):
                namespace = tokens_lower[i + 1]
                break
            if t.startswith("--namespace="):
                namespace = t.split("=", 1)[1]
                break

        # Block delete in system namespaces
        if is_delete and namespace in self.BLOCKED_NAMESPACES:
            errors.append(f"Delete in system namespace is blocked: {namespace}")

        # Warn about delete without explicit namespace (defaults to 'default')
        if is_delete and not namespace and "--all-namespaces" not in tokens_lower and "-a" not in tokens_lower:
            warnings.append("Deleting in default namespace; consider specifying -n")

        # Force delete warning
        if is_delete and ("--force" in tokens_lower or "--grace-period=0" in tokens_lower):
            warnings.append("Force delete / grace period override detected")

        # Cluster-admin operations warning
        if "clusterrolebinding" in tokens_lower or "clusterrole" in tokens_lower:
            warnings.append("Cluster-admin level operation detected")

        # Validate kubectl get resource type
        if is_get and len(tokens_lower) >= 3:
            resource = tokens_lower[2]
            allowed_resources = {
                "pods", "pod", "deployments", "deployment", "services", "service", "svc",
                "namespaces", "namespace", "ns", "nodes", "node", "ingress", "ingresses",
                "configmap", "configmaps", "secret", "secrets", "crd", "crds", "crds.v1",
                "pv", "pvs", "pvc", "pvcs", "events", "event", "jobs", "job",
                "replicasets", "replicaset", "statefulsets", "statefulset", "daemonsets", "daemonset",
            }
            if resource not in allowed_resources and "/" not in resource:
                errors.append(f"Invalid resource type: {resource}")

        # apply -f file existence warning
        if len(tokens_lower) >= 2 and tokens_lower[1] == "apply":
            if "-f" in tokens_lower:
                idx = tokens_lower.index("-f")
                if idx + 1 < len(tokens):
                    path = tokens[idx + 1]
                    try:
                        from pathlib import Path

                        if path.endswith((".yml", ".yaml")) and not Path(path).expanduser().exists():
                            warnings.append(f"File not found: {path}")
                    except Exception:
                        pass

        if is_port_forward:
            warnings.append("Port forward operation detected")

        if is_logs and ("--all-namespaces" in tokens_lower or "-a" in tokens_lower):
            warnings.append("Logs across all namespaces requested")

        if "--watch" in tokens_lower:
            warnings.append("Watch operation requested")

        # Validate replicas for scale
        if is_scale:
            replicas_val: Optional[str] = None
            for t in tokens_lower:
                if t.startswith("--replicas="):
                    replicas_val = t.split("=", 1)[1]
                    break
            if replicas_val is not None:
                try:
                    replicas_int = int(replicas_val)
                    if replicas_int < 0:
                        errors.append("Replica count cannot be negative")
                except Exception:
                    errors.append("Invalid replica count")

        # Delete across all namespaces is dangerous
        if is_delete and ("-a" in tokens_lower or "--all-namespaces" in tokens_lower or "-A" in tokens):
            errors.append("Delete across all namespaces is very dangerous")

        # General suggestion: specify namespace if missing
        if is_kubectl_cmd and not namespace and "--all-namespaces" not in tokens_lower and "-a" not in tokens_lower and "-A" not in tokens:
            suggestions.append("Consider specifying namespace with -n")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

