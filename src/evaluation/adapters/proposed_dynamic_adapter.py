"""The proposed model shares the encoder/CRF adapter and audited structure policy."""

from src.evaluation.adapters.phobert_crf_adapter import PhoBERTCRFAdapter


class ProposedDynamicAdapter(PhoBERTCRFAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.config.get("t1_implemented"):
            raise ValueError("PROPOSED_REQUIRES_THREE_CLASS_T1_HEAD")
