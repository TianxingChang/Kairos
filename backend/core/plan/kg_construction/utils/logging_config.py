"""Logging configuration for knowledge graph construction."""

import logging
import sys
from pathlib import Path
from typing import Optional
from core.plan.kg_construction.config.settings import Settings


def setup_logging(settings: Optional[Settings] = None) -> None:
    """Setup logging configuration.
    
    Args:
        settings: Application settings (optional).
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ) 