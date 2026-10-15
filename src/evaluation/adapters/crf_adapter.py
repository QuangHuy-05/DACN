"""Independent linear-chain CRF; inference consumes original text only."""

from __future__ import annotations

import json
from pathlib import Path
import time

from src.evaluation.adapters.base import BaseAddressParser, BaseSpanAddressParser
from src.evaluation.schema import SpanModelOutput
from src.evaluation.span_features import FEATURE_VERSION, FOLLOWUP_FEATURE_VERSION, TOKENIZER_VERSION, decode_bio, tokenize, token_features


class IndependentCRFAdapter(BaseAddressParser, BaseSpanAddressParser):
    def __init__(self, checkpoint_path: str, metadata_path: str):
        import pycrfsuite
        self.metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
        if self.metadata["tokenizer_version"] != TOKENIZER_VERSION or self.metadata["feature_version"] not in (FEATURE_VERSION, FOLLOWUP_FEATURE_VERSION):
            raise ValueError("CRF feature/tokenizer version mismatch")
        self.tagger = pycrfsuite.Tagger()
        self.tagger.open(str(checkpoint_path))

    @property
    def tool_name(self) -> str:
        return "CRF-INDEP"

    def parse_spans(self, raw_address: str, sample_id: str = "", **kwargs) -> SpanModelOutput:
        started = time.perf_counter()
        tokens = tokenize(raw_address)
        if not tokens:
            return SpanModelOutput(sample_id, raw_address, abstain=True, status="abstain")
        tags = self.tagger.tag(token_features(raw_address, tokens, self.metadata["context"], self.metadata["feature_version"]))
        spans, repairs = decode_bio(raw_address, tokens, tags)
        # This configuration trains T0 only. No hidden T1 classifier.
        return SpanModelOutput(sample_id, raw_address, spans, predicted_system="khong_ro",
            abstain=not bool(spans), latency_ms=(time.perf_counter()-started)*1000,
            trace={"bio_repairs": repairs, "t1": "NOT_IMPLEMENTED", "truncation": "none"},
            raw_output={"tokens": [vars(token) for token in tokens], "bio_tags": tags})

    def parse(self, raw_address: str, **kwargs):
        output = self.parse_spans(raw_address)
        return output.to_standard_5_fields(), output.to_dict()
