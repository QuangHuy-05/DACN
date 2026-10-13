"""Local-only PhoBERT inference on raw text; gold never enters this adapter."""

from src.evaluation.adapters.base import BaseSpanAddressParser
from src.evaluation.dev_runner import ROOT, file_hash
from src.evaluation.schema import SpanModelOutput
from src.evaluation.span_features import BIO_LABELS
from src.modeling.alignment import decode_tags
from src.modeling.checkpoints import load_checkpoint
from src.modeling.resources import preflight, validate_resource_lock, load_phobert_processor
from src.modeling.structural_decoder import structure_decision


class PhoBERTCRFAdapter(BaseSpanAddressParser):
    def __init__(self, checkpoint_path=None, resource_lock_path=None, config=None, model=None, processor=None, decoder_policy=None):
        self.config = config or {"device": "cpu", "t1_implemented": False}
        if model is None or processor is None:
            from src.modeling.training import create_phobert_model
            resource_path = ROOT / resource_lock_path
            result = preflight(config, resource_path)
            if result["blockers"]:
                raise RuntimeError(str(result["blockers"]))
            lock = validate_resource_lock(resource_path, config["model_id"])
            model = create_phobert_model(config, lock)
            load_checkpoint(ROOT / checkpoint_path, config, config["corpus_manifest_sha256"], file_hash(resource_path), model)
            processor = load_phobert_processor(config, lock)
        self.model, self.processor = model.to(self.config["device"]), processor
        self.decoder_policy = decoder_policy or self.config.get("structural_policy")
        if self.config.get("t1_implemented") and decoder_policy is not None:
            from src.modeling.calibration import CONFIDENCE_GRID
            if decoder_policy.get("version") != "confidence_bio_constraint_v1" or (decoder_policy.get("threshold"), decoder_policy.get("margin")) not in CONFIDENCE_GRID or decoder_policy.get("enabled") is not (self.config["model_id"] == "PROPOSED-DYN"):
                raise ValueError("DECODER_POLICY_OUTSIDE_LOCKED_CALIBRATION_OR_ABLATION")
        self.model.eval()

    @property
    def tool_name(self):
        return self.config.get("model_id", "PHOBERT-CRF")

    def parse_spans(self, raw_address, sample_id="", **kwargs):
        import torch
        try:
            alignment = self.processor.align_text(raw_address)
        except ValueError as exc:
            return SpanModelOutput(sample_id, raw_address, abstain=True, status="abstain", error=str(exc),
                                   trace={"processor": self.processor.version, "alignment_reject": str(exc)})
        ids = torch.tensor([alignment.input_ids], device=self.config["device"])
        self.model.eval()
        with torch.no_grad():
            result = self.model(ids, torch.ones_like(ids), [alignment.unit_to_model])
            original = self.model.crf.decode(result["emissions"], result["mask"])[0]
            decision, path, system = None, original, "khong_ro"
            if self.config.get("t1_implemented"):
                posterior = result["t1_logits"].softmax(-1)[0].cpu().tolist()
                policy = self.decoder_policy
                decision = structure_decision(posterior, policy["threshold"], policy["margin"], policy["enabled"])
                path = self.model.crf.decode(result["emissions"], result["mask"], decision["forbidden_tag_ids"])[0]
                system = decision["predicted_system"]
        spans, _ = decode_tags(alignment, [BIO_LABELS[i] for i in path])
        prior_spans, _ = decode_tags(alignment, [BIO_LABELS[i] for i in original])
        trace = {"alignment": alignment.to_dict(), "path_before_constraint": original, "path_after_constraint": path,
                 "spans_before_constraint": [s.to_dict() for s in prior_spans], "structure": decision,
                 "changed_unit_indices": [i for i, (a, b) in enumerate(zip(original, path)) if a != b],
                 "t1_task": "IMPLEMENTED" if self.config.get("t1_implemented") else "NOT_IMPLEMENTED"}
        # T1-only abstention retains valid T0 spans; runner.abstain means no usable T0.
        return SpanModelOutput(sample_id, raw_address, spans, predicted_system=system, trace=trace,
            raw_output={"emissions": result["emissions"][0].cpu().tolist(), "tags": [BIO_LABELS[i] for i in path]})

    def parse(self, raw_address, **kwargs):
        output = self.parse_spans(raw_address)
        return output.to_standard_5_fields(), output.raw_output
