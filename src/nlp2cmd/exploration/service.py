"""
Service Explorer - API and service endpoint discovery.

Find endpoints, methods, and schemas in REST APIs, GraphQL, etc.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from nlp2cmd.exploration.base import BaseExplorer, ExplorationContext, ExplorationResult


@dataclass
class EndpointInfo:
    """Information about an API endpoint."""
    url: str
    method: str = "GET"
    name: str = ""
    description: Optional[str] = None
    parameters: list[dict[str, Any]] = field(default_factory=list)
    response_schema: Optional[dict[str, Any]] = None
    requires_auth: bool = False
    tags: list[str] = field(default_factory=list)


@dataclass
class ServiceInfo:
    """Information about a service."""
    name: str
    base_url: str
    version: Optional[str] = None
    endpoints: list[EndpointInfo] = field(default_factory=list)
    auth_type: Optional[str] = None  # bearer, api_key, oauth, etc.


class ServiceExplorer(BaseExplorer):
    """Explorer for REST APIs, GraphQL, and other services."""
    
    def __init__(
        self,
        max_depth: int = 2,
        max_results: int = 20,
        timeout_seconds: float = 10.0,
        auth_token: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__(max_depth, max_results, timeout_seconds)
        self.auth_token = auth_token
        self.api_key = api_key
        self._discovered_paths: set[str] = set()
    
    def supports(self, space_type: str) -> bool:
        return space_type in ("service", "api", "endpoint", "rest", "graphql")
    
    def explore(
        self,
        root: Any,
        context: ExplorationContext,
    ) -> ExplorationResult[EndpointInfo]:
        """Explore API/service starting from base URL."""
        base_url = str(root).rstrip("/")
        
        if not base_url.startswith(("http://", "https://")):
            return ExplorationResult(
                success=False,
                error=f"Invalid service URL: {base_url}",
            )
        
        candidates: list[EndpointInfo] = []
        
        # Try to discover via OpenAPI/Swagger
        openapi_endpoints = self._try_openapi_discovery(base_url, context)
        candidates.extend(openapi_endpoints)
        
        # Try common REST patterns
        if not candidates:
            rest_endpoints = self._try_rest_discovery(base_url, context)
            candidates.extend(rest_endpoints)
        
        # Try GraphQL introspection
        if not candidates:
            graphql_endpoints = self._try_graphql_discovery(base_url, context)
            candidates.extend(graphql_endpoints)
        
        if not candidates:
            return ExplorationResult(
                success=False,
                error=f"No endpoints found at {base_url}",
                candidates=[],
            )
        
        # Score and sort
        scored = [(self._score_endpoint(ep, context), ep) for ep in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        
        best = scored[0][1] if scored else None
        
        return ExplorationResult(
            success=True,
            target=best,
            path=[best.url] if best else [],
            candidates=[ep for _, ep in scored],
            metadata={
                "base_url": base_url,
                "search_term": context.search_term,
                "intent": context.intent,
                "total_endpoints": len(candidates),
            },
        )
    
    def _try_openapi_discovery(
        self,
        base_url: str,
        context: ExplorationContext,
    ) -> list[EndpointInfo]:
        """Try to discover endpoints via OpenAPI spec."""
        import urllib.request
        
        endpoints: list[EndpointInfo] = []
        
        # Common OpenAPI paths
        openapi_paths = [
            "/openapi.json",
            "/swagger.json",
            "/api-docs",
            "/v2/api-docs",
            "/api/swagger.json",
        ]
        
        for path in openapi_paths:
            try:
                spec_url = urljoin(base_url, path)
                req = urllib.request.Request(
                    spec_url,
                    headers=self._get_headers(),
                    method="GET",
                )
                
                with urllib.request.urlopen(req, timeout=int(self.timeout_seconds)) as resp:
                    if resp.status == 200:
                        spec = json.loads(resp.read().decode("utf-8"))
                        endpoints = self._parse_openapi_spec(spec, base_url)
                        if endpoints:
                            break
            except Exception:
                continue
        
        return endpoints
    
    def _parse_openapi_spec(self, spec: dict[str, Any], base_url: str) -> list[EndpointInfo]:
        """Parse OpenAPI spec and extract endpoints."""
        endpoints: list[EndpointInfo] = []
        
        try:
            paths = spec.get("paths", {})
            for path, methods in paths.items():
                for method, details in methods.items():
                    if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                        endpoint = EndpointInfo(
                            url=urljoin(base_url, path),
                            method=method.upper(),
                            name=details.get("summary", ""),
                            description=details.get("description"),
                            parameters=details.get("parameters", []),
                            tags=details.get("tags", []),
                        )
                        endpoints.append(endpoint)
        except Exception:
            pass
        
        return endpoints
    
    def _try_rest_discovery(
        self,
        base_url: str,
        context: ExplorationContext,
    ) -> list[EndpointInfo]:
        """Try common REST API patterns."""
        endpoints: list[EndpointInfo] = []
        
        # Common REST resource patterns
        resource_patterns = [
            "/api/v1/{resource}",
            "/api/{resource}",
            "/v1/{resource}",
            "/rest/{resource}",
            "/{resource}",
        ]
        
        resources = self._get_resource_names(context)
        
        for resource in resources:
            for pattern in resource_patterns:
                path = pattern.replace("{resource}", resource)
                endpoint = EndpointInfo(
                    url=urljoin(base_url, path),
                    method="GET",
                    name=f"Get {resource}",
                )
                endpoints.append(endpoint)
        
        return endpoints
    
    def _try_graphql_discovery(
        self,
        base_url: str,
        context: ExplorationContext,
    ) -> list[EndpointInfo]:
        """Try GraphQL introspection."""
        endpoints: list[EndpointInfo] = []
        
        # Common GraphQL paths
        graphql_paths = ["/graphql", "/api/graphql", "/query"]
        
        for path in graphql_paths:
            try:
                import urllib.request
                
                graphql_url = urljoin(base_url, path)
                
                # Try introspection query
                introspection_query = {
                    "query": """
                    {
                        __schema {
                            queryType { name }
                            mutationType { name }
                        }
                    }
                    """
                }
                
                req = urllib.request.Request(
                    graphql_url,
                    data=json.dumps(introspection_query).encode("utf-8"),
                    headers={
                        **self._get_headers(),
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                
                with urllib.request.urlopen(req, timeout=int(self.timeout_seconds)) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        if data.get("data", {}).get("__schema"):
                            endpoint = EndpointInfo(
                                url=graphql_url,
                                method="POST",
                                name="GraphQL Endpoint",
                                description="GraphQL API endpoint",
                                tags=["graphql"],
                            )
                            endpoints.append(endpoint)
                            break
            except Exception:
                continue
        
        return endpoints
    
    def _get_resource_names(self, context: ExplorationContext) -> list[str]:
        """Get common REST resource names based on context."""
        # Default resources
        resources = [
            "users", "items", "products", "orders", "customers",
            "posts", "comments", "categories", "tags", "files",
            "config", "settings", "status", "health", "info",
        ]
        
        # Add context-specific resources
        if context.search_term:
            resources.insert(0, context.search_term.lower())
        
        # Add intent-specific resources
        if context.intent == "user":
            resources = ["users", "accounts", "profiles", "auth"] + resources
        elif context.intent == "product":
            resources = ["products", "items", "catalog", "inventory"] + resources
        elif context.intent == "data":
            resources = ["data", "records", "entities", "resources"] + resources
        
        return resources
    
    def _get_headers(self) -> dict[str, str]:
        """Get request headers with auth if configured."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "nlp2cmd-service-explorer/1.0",
        }
        
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        elif self.api_key:
            headers["X-API-Key"] = self.api_key
        
        return headers
    
    def _score_endpoint(self, endpoint: EndpointInfo, context: ExplorationContext) -> float:
        """Score endpoint relevance."""
        score = super()._score_relevance(endpoint.url, context)
        
        # Boost for matching search term in name
        if context.search_term and endpoint.name:
            search_lower = context.search_term.lower()
            name_lower = endpoint.name.lower()
            
            if search_lower in name_lower:
                score += 2.0
        
        # Boost for GET method (usually more accessible)
        if endpoint.method == "GET":
            score += 0.5
        
        # Boost for not requiring auth
        if not endpoint.requires_auth:
            score += 0.3
        
        return score


def quick_find_endpoint(
    base_url: str,
    search_term: str,
    auth_token: Optional[str] = None,
) -> Optional[str]:
    """Quick helper to find API endpoint URL."""
    explorer = ServiceExplorer(auth_token=auth_token)
    context = ExplorationContext(
        intent="endpoint",
        search_term=search_term,
    )
    result = explorer.explore(base_url, context)
    return result.target.url if result.target else None
