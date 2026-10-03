"""BIO24 Deepparse fine-tuned adapter, kept separate from native zero-shot tags."""

from pathlib import Path

from src.evaluation.adapters.base import BaseSpanAddressParser
from src.evaluation.dev_runner import ROOT, file_hash
from src.evaluation.schema import SpanModelOutput
from src.modeling.alignment import DeepparseProcessor
from src.modeling.checkpoints import load_checkpoint
from src.modeling.deepparse_training import construct_parser, decode_native_ids, native_inference
from src.modeling.resources import preflight, validate_resource_lock


class DeepparseFinetunedAdapter(BaseSpanAddressParser):
    def __init__(self, checkpoint_path=None, resource_lock_path=None, config=None, parser=None):
        self.config = config or {}
        self.processor = DeepparseProcessor()
        if parser is None:
            resource_path = ROOT / resource_lock_path
            result = preflight(config, resource_path)
            if result["blockers"]:
                raise RuntimeError(str(result["blockers"]))
            lock = validate_resource_lock(resource_path, config["model_id"])
            checkpoint = ROOT / checkpoint_path
            load_checkpoint(checkpoint, config, config["corpus_manifest_sha256"], file_hash(resource_path))
            parser = construct_parser(lock, config["device"], checkpoint)
        self.parser = parser

    @property
    def tool_name(self):
        return "DP-FT-FT"

    def parse_spans(self, raw_address, sample_id="", **kwargs):
        try:
            alignment = self.processor.align_text(raw_address)
        except ValueError as exc:
            return SpanModelOutput(sample_id, raw_address, abstain=True, status="abstain", error=str(exc),
                                   trace={"processor": self.processor.version, "alignment_reject": str(exc)})
        ids, raw = native_inference(self.parser, alignment)
        try:
            spans, trace = decode_native_ids(alignment, ids)
        except ValueError as exc:
            return SpanModelOutput(sample_id, raw_address, abstain=True, status="abstain",
                raw_output={**raw, "native_tag_ids": ids}, error=str(exc), trace={"alignment": alignment.to_dict()})
        return SpanModelOutput(sample_id, raw_address, spans, raw_output={**raw, **trace},
            trace={"alignment": alignment.to_dict(), "native_decode": trace, "t1_task": "NOT_IMPLEMENTED"})

    def parse(self, raw_address, **kwargs):
        output = self.parse_spans(raw_address)
        return output.to_standard_5_fields(), output.raw_output
