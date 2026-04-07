"""
cpt_core - Pluggable library for CPT regression analysis.

Exports:
    CPTConfig              - Configuration dataclass
    RegressionAnalyzer     - High-level orchestrator
    AIProvider             - Abstract AI provider interface
    OpenAICompatibleProvider - Concrete OpenAI-compatible implementation
    ComparisonResult       - Result dataclass from compare()
"""

from .config import CPTConfig
from .analysis import ComparisonResult
from .ai_provider import AIProvider, OpenAICompatibleProvider
from .orchestrator import RegressionAnalyzer

__all__ = [
    "CPTConfig",
    "ComparisonResult",
    "AIProvider",
    "OpenAICompatibleProvider",
    "RegressionAnalyzer",
]
