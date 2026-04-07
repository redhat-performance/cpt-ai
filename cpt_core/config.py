"""
CPTConfig - Configuration dataclass for the CPT core library.

Holds all settings needed by data access, AI provider, and orchestrator layers.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv


@dataclass
class CPTConfig:
    """Configuration for the CPT regression analysis pipeline."""

    mcp_url: str = "http://localhost:9900/sse"
    opensearch_cluster: str = "zathras"
    opensearch_index: str = "zathras-results"

    ai_endpoint: str = ""
    ai_api_key: str = ""
    ai_model: str = "granite-3-3-8b-instruct"
    ssl_verify: bool = False

    @classmethod
    def from_env(cls) -> "CPTConfig":
        """Load configuration from environment variables / .env file."""
        load_dotenv()

        return cls(
            mcp_url=os.getenv("MCP_URL", "http://localhost:9900/sse"),
            opensearch_cluster=os.getenv("OPENSEARCH_CLUSTER", "zathras"),
            opensearch_index=os.getenv("OPENSEARCH_INDEX", "zathras-results"),
            ai_endpoint=os.getenv("MODELS_CORP_ENDPOINT", ""),
            ai_api_key=os.getenv("MODELS_CORP_API_KEY", ""),
            ai_model=os.getenv("MODEL_NAME", "granite-3-3-8b-instruct"),
            ssl_verify=os.getenv("SSL_VERIFY", "false").lower() == "true",
        )
