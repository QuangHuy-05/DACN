"""Abstract base class for baseline address parsers and converters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.evaluation.schema import StandardPrediction


class BaseAddressParser(ABC):
    """Abstract interface for baseline address parsers."""

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Name of the baseline tool."""
        pass

    @abstractmethod
    def parse(self, raw_address: str, **kwargs: Any) -> tuple[StandardPrediction, Any]:
        """Parse raw address string into StandardPrediction without ground truth hints.
        
        Returns:
            tuple of (StandardPrediction, raw_response_data)
        """
        pass
