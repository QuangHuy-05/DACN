"""Abstract base class for baseline address parsers and converters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.evaluation.schema import SpanModelOutput, StandardPrediction


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


class BaseSpanAddressParser(ABC):
    """Abstract interface for T0/T1 span-based address parsers."""

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Name of the baseline or proposed model."""
        pass

    @abstractmethod
    def parse_spans(
        self, raw_address: str, sample_id: str = "", **kwargs: Any
    ) -> SpanModelOutput:
        """Parse raw address string into 11-span and T1 system output."""
        pass
