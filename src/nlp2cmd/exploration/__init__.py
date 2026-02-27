"""
Exploration package - Universal exploration across different spaces.

Provides exploration capabilities for:
- Web (websites, forms, content)
- Disk (file systems, directories)
- Services (APIs, endpoints)
- Data Trees (JSON, nested structures)

Usage:
    # Auto-detect and explore
    from nlp2cmd.exploration import explore
    result = explore("https://example.com", "contact")
    
    # Specific explorers
    from nlp2cmd.exploration import DiskExplorer, ServiceExplorer
    
    disk = DiskExplorer()
    files = disk.find_config("~", app_name="myapp")
    
    service = ServiceExplorer()
    endpoint = service.explore("https://api.example.com", 
                                ExplorationContext(intent="user"))
"""

from nlp2cmd.exploration.base import (
    BaseExplorer,
    ExplorationContext,
    ExplorationResult,
    ExplorerRegistry,
    explore,
)
from nlp2cmd.exploration.disk import (
    DiskExplorer,
    FileInfo,
    quick_find_file,
)
from nlp2cmd.exploration.service import (
    EndpointInfo,
    ServiceExplorer,
    ServiceInfo,
    quick_find_endpoint,
)
from nlp2cmd.exploration.data_tree import (
    DataMatch,
    DataNode,
    DataTreeExplorer,
    quick_find_in_data,
)
from nlp2cmd.exploration.resource_discovery import (
    ResourceDiscoveryManager,
    MissingResource,
    DiscoveryDecision,
    get_resource_discovery_manager,
)

# Import and register web explorer if available
try:
    from nlp2cmd.web_schema.site_explorer import SiteExplorer as WebExplorer
    
    # Register web explorer
    ExplorerRegistry.register("web", WebExplorer())
    ExplorerRegistry.register("website", WebExplorer())
except ImportError:
    WebExplorer = None  # type: ignore

# Register all explorers
ExplorerRegistry.register("disk", DiskExplorer())
ExplorerRegistry.register("file", DiskExplorer())
ExplorerRegistry.register("fs", DiskExplorer())
ExplorerRegistry.register("service", ServiceExplorer())
ExplorerRegistry.register("api", ServiceExplorer())
ExplorerRegistry.register("endpoint", ServiceExplorer())
ExplorerRegistry.register("data", DataTreeExplorer())
ExplorerRegistry.register("json", DataTreeExplorer())
ExplorerRegistry.register("tree", DataTreeExplorer())

__all__ = [
    # Base
    "BaseExplorer",
    "ExplorationContext",
    "ExplorationResult",
    "ExplorerRegistry",
    "explore",
    # Disk
    "DiskExplorer",
    "FileInfo",
    "quick_find_file",
    # Service
    "ServiceExplorer",
    "ServiceInfo",
    "EndpointInfo",
    "quick_find_endpoint",
    # Data
    "DataTreeExplorer",
    "DataNode",
    "DataMatch",
    "quick_find_in_data",
    # Resource Discovery (Execution Integration)
    "ResourceDiscoveryManager",
    "MissingResource",
    "DiscoveryDecision",
    "get_resource_discovery_manager",
    # Web (optional)
    "WebExplorer",
]
