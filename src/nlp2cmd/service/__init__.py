"""
Service module for NLP2CMD - HTTP API server mode.
"""

from __future__ import annotations

import json
import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

try:
    from pydantic import BaseModel, Field
except ImportError:
    BaseModel = object
    Field = lambda x, **kwargs: x

# FastAPI/uvicorn are intentionally imported lazily to keep CLI startup fast.
FastAPI = None
HTTPException = None
BackgroundTasks = None
JSONResponse = None
CORSMiddleware = None
uvicorn = None

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import FastAPI as _FastAPI, HTTPException as _HTTPException, BackgroundTasks as _BackgroundTasks
    from fastapi.responses import JSONResponse as _JSONResponse
    from fastapi.middleware.cors import CORSMiddleware as _CORSMiddleware


def _ensure_service_deps() -> None:
    """Lazily import FastAPI/uvicorn dependencies for service mode."""
    global FastAPI, HTTPException, BackgroundTasks, JSONResponse, CORSMiddleware, uvicorn

    if FastAPI is not None and uvicorn is not None:
        return

    from fastapi import FastAPI as _FastAPI, HTTPException as _HTTPException, BackgroundTasks as _BackgroundTasks
    from fastapi.responses import JSONResponse as _JSONResponse
    from fastapi.middleware.cors import CORSMiddleware as _CORSMiddleware
    import uvicorn as _uvicorn

    FastAPI = _FastAPI
    HTTPException = _HTTPException
    BackgroundTasks = _BackgroundTasks
    JSONResponse = _JSONResponse
    CORSMiddleware = _CORSMiddleware
    uvicorn = _uvicorn


from ..generation.pipeline import RuleBasedPipeline
from ..cli.display import display_command_result


class ServiceConfig:
    """Configuration for NLP2CMD service."""
    
    def __init__(self):
        self.host = os.getenv("NLP2CMD_HOST", "0.0.0.0")
        self.port = int(os.getenv("NLP2CMD_PORT", "8000"))
        self.debug = os.getenv("NLP2CMD_DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("NLP2CMD_LOG_LEVEL", "info")
        self.cors_origins = os.getenv("NLP2CMD_CORS_ORIGINS", "*").split(",")
        self.max_workers = int(os.getenv("NLP2CMD_MAX_WORKERS", "4"))
        
        # LLM Configuration
        self.llm_model = os.getenv("LITELLM_MODEL", "ollama/qwen2.5-coder:7b")
        self.llm_api_base = os.getenv("LITELLM_API_BASE", "http://localhost:11434")
        self.llm_api_key = os.getenv("LITELLM_API_KEY", "")
        self.llm_temperature = float(os.getenv("LITELLM_TEMPERATURE", "0.1"))
        self.llm_max_tokens = int(os.getenv("LITELLM_MAX_TOKENS", "2048"))
        self.llm_timeout = int(os.getenv("LITELLM_TIMEOUT", "30"))
        
        # Service-specific settings
        self.auto_execute = os.getenv("NLP2CMD_AUTO_EXECUTE", "false").lower() == "true"
        self.session_timeout = int(os.getenv("NLP2CMD_SESSION_TIMEOUT", "3600"))  # seconds
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "host": self.host,
            "port": self.port,
            "debug": self.debug,
            "log_level": self.log_level,
            "cors_origins": self.cors_origins,
            "max_workers": self.max_workers,
            "llm_model": self.llm_model,
            "llm_api_base": self.llm_api_base,
            "llm_temperature": self.llm_temperature,
            "llm_max_tokens": self.llm_max_tokens,
            "llm_timeout": self.llm_timeout,
            "auto_execute": self.auto_execute,
            "session_timeout": self.session_timeout
        }
    
    def save_to_env(self, env_file: Optional[str] = None):
        """Save configuration to .env file."""
        if env_file is None:
            env_file = ".env"
        
        env_path = Path(env_file)
        
        # Read existing .env file
        existing_vars = {}
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        existing_vars[key] = value
        
        # Update with service config
        service_vars = {
            "NLP2CMD_HOST": self.host,
            "NLP2CMD_PORT": str(self.port),
            "NLP2CMD_DEBUG": str(self.debug).lower(),
            "NLP2CMD_LOG_LEVEL": self.log_level,
            "NLP2CMD_CORS_ORIGINS": ",".join(self.cors_origins),
            "NLP2CMD_MAX_WORKERS": str(self.max_workers),
            "NLP2CMD_AUTO_EXECUTE": str(self.auto_execute).lower(),
            "NLP2CMD_SESSION_TIMEOUT": str(self.session_timeout),
        }
        
        existing_vars.update(service_vars)
        
        # Write back to file
        with open(env_path, 'w') as f:
            f.write("# NLP2CMD Service Configuration\n")
            f.write("# Generated automatically by nlp2cmd service\n\n")
            
            for key, value in sorted(existing_vars.items()):
                f.write(f"{key}={value}\n")


class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    query: str = Field(..., description="Natural language query to process")
    dsl: str = Field(default="auto", description="DSL type to use")
    explain: bool = Field(default=False, description="Include explanation in response")
    execute: bool = Field(default=False, description="Execute the generated command")


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    success: bool
    command: Optional[str] = None
    explanation: Optional[str] = None
    confidence: Optional[float] = None
    domain: Optional[str] = None
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    errors: Optional[list] = None
    warnings: Optional[list] = None
    execution_result: Optional[Dict[str, Any]] = None


class NLP2CMDService:
    """NLP2CMD HTTP API Service."""
    
    def __init__(self, config: Optional[ServiceConfig] = None):
        self.config = config or ServiceConfig()
        self.app = None
        self.pipeline = None
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def _create_app(self) -> 'FastAPI':
        """Create FastAPI application."""
        _ensure_service_deps()

        app = FastAPI(
            title="NLP2CMD API",
            description="Natural Language to Domain-Specific Commands API",
            version="1.0.0",
            debug=self.config.debug
        )
        
        # Add CORS middleware
        if CORSMiddleware is not None:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        
        # Initialize pipeline
        self.pipeline = RuleBasedPipeline()
        
        return app
    
    def _setup_routes(self, app: 'FastAPI'):
        """Setup API routes."""
        
        @app.get("/")
        async def root():
            """Root endpoint with service info."""
            return {
                "service": "NLP2CMD API",
                "version": "1.0.0",
                "status": "running",
                "config": self.config.to_dict()
            }
        
        @app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "service": "nlp2cmd"}
        
        @app.post("/query", response_model=QueryResponse)
        async def process_query(request: QueryRequest, background_tasks: BackgroundTasks):
            """Process natural language query."""
            try:
                should_execute = bool(request.execute or self.config.auto_execute)

                # Process query using pipeline
                result = self.pipeline.process(request.query)
                
                response_data = {
                    "success": result.success,
                    "command": result.command if result.success else None,
                    "confidence": result.confidence,
                    "domain": result.domain,
                    "intent": result.intent,
                    "entities": result.entities,
                    "metadata": result.metadata,
                    "errors": result.errors if not result.success else None,
                    "warnings": []
                }
                
                # Add explanation if requested
                if request.explain:
                    response_data["explanation"] = f"Generated by RuleBasedPipeline with confidence {result.confidence:.2f}"
                
                # Execute command if requested
                if should_execute and result.success and result.command:
                    try:
                        if result.domain == "sql":
                            response_data["execution_result"] = {
                                "success": False,
                                "error": "Refusing to execute SQL as a shell command",
                            }
                            return QueryResponse(**response_data)

                        # Import inside function to avoid circular dependency
                        from ..execution.runner import ExecutionRunner
                        runner = ExecutionRunner(
                            console=None,
                            auto_confirm=True,
                            max_retries=1,
                            plain_output=True,
                        )
                        exec_result = runner.run_with_recovery(result.command, request.query)
                        
                        response_data["execution_result"] = {
                            "success": exec_result.success,
                            "exit_code": exec_result.exit_code,
                            "stdout": exec_result.stdout,
                            "stderr": exec_result.stderr,
                            "duration_ms": exec_result.duration_ms
                        }
                    except Exception as e:
                        response_data["execution_result"] = {
                            "success": False,
                            "error": str(e)
                        }
                
                return QueryResponse(**response_data)
                
            except Exception as e:
                self.logger.error(f"Error processing query: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/config")
        async def get_config():
            """Get current service configuration."""
            return self.config.to_dict()
        
        @app.post("/config")
        async def update_config(config_updates: Dict[str, Any]):
            """Update service configuration."""
            try:
                for key, value in config_updates.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)
                        # Also update environment variable
                        os.environ[f"NLP2CMD_{key.upper()}"] = str(value)
                
                return {"message": "Configuration updated", "config": self.config.to_dict()}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @app.post("/config/save")
        async def save_config(env_file: Optional[str] = None):
            """Save current configuration to .env file."""
            try:
                self.config.save_to_env(env_file)
                return {"message": f"Configuration saved to {env_file or '.env'}"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    
    def run(self, host: Optional[str] = None, port: Optional[int] = None, **kwargs):
        """Run the service."""
        _ensure_service_deps()
        
        # Override config with command line arguments
        run_host = host or self.config.host
        run_port = port or self.config.port
        
        # Create and setup app
        self.app = self._create_app()
        self._setup_routes(self.app)
        
        self.logger.info(f"Starting NLP2CMD service on {run_host}:{run_port}")
        
        # Always use import string for consistency
        # Set environment variables for the factory function
        original_debug = os.environ.get("NLP2CMD_DEBUG")
        original_log_level = os.environ.get("NLP2CMD_LOG_LEVEL")
        original_host = os.environ.get("NLP2CMD_HOST")
        original_port = os.environ.get("NLP2CMD_PORT")
        
        try:
            os.environ["NLP2CMD_DEBUG"] = str(self.config.debug).lower()
            os.environ["NLP2CMD_LOG_LEVEL"] = self.config.log_level
            os.environ["NLP2CMD_HOST"] = run_host
            os.environ["NLP2CMD_PORT"] = str(run_port)
            
            uvicorn.run(
                "nlp2cmd.service:create_app",
                host=run_host,
                port=run_port,
                log_level=self.config.log_level,
                factory=True,
                **kwargs
            )
        finally:
            # Restore original environment variables
            if original_debug is not None:
                os.environ["NLP2CMD_DEBUG"] = original_debug
            else:
                os.environ.pop("NLP2CMD_DEBUG", None)
            if original_log_level is not None:
                os.environ["NLP2CMD_LOG_LEVEL"] = original_log_level
            else:
                os.environ.pop("NLP2CMD_LOG_LEVEL", None)
            if original_host is not None:
                os.environ["NLP2CMD_HOST"] = original_host
            else:
                os.environ.pop("NLP2CMD_HOST", None)
            if original_port is not None:
                os.environ["NLP2CMD_PORT"] = original_port
            else:
                os.environ.pop("NLP2CMD_PORT", None)


def create_app() -> 'FastAPI':
    """Create FastAPI application for uvicorn import."""
    _ensure_service_deps()
    # Read configuration from environment variables (for workers/reload mode)
    config = ServiceConfig()
    service = NLP2CMDService(config)
    app = service._create_app()
    service._setup_routes(app)
    return app


def create_service_config_from_args(
    host: str = "0.0.0.0",
    port: int = 8000,
    debug: bool = False,
    log_level: str = "info",
    cors_origins: str = "*",
    max_workers: int = 4,
    auto_execute: bool = False,
    session_timeout: int = 3600,
    save_env: bool = False,
    env_file: Optional[str] = None
) -> ServiceConfig:
    """Create ServiceConfig from command line arguments."""
    config = ServiceConfig()
    
    # Override with command line arguments
    config.host = host
    config.port = port
    config.debug = debug
    config.log_level = log_level
    config.cors_origins = cors_origins.split(",") if isinstance(cors_origins, str) else cors_origins
    config.max_workers = max_workers
    config.auto_execute = auto_execute
    config.session_timeout = session_timeout
    
    # Save to .env if requested
    if save_env:
        config.save_to_env(env_file)
        print(f"Configuration saved to {env_file or '.env'}")
    
    return config
