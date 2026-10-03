"""Shared T0 CRF and three-class T1; abstention belongs to inference only."""

from src.modeling.phobert_crf import PhoBERTCRF, torch, nn


if nn is not None:
    class ProposedDynamic(PhoBERTCRF):
        def __init__(self, encoder, hidden_size=None, dropout=0.1, t1_loss_weight=0.5):
            super().__init__(encoder, hidden_size, dropout)
            self.t1_head = nn.Linear(hidden_size or encoder.config.hidden_size, 3)
            self.t1_loss_weight = t1_loss_weight

        def forward(self, input_ids, attention_mask, unit_to_model, tags=None, t1_targets=None, t1_mask=None):
            output = super().forward(input_ids, attention_mask, unit_to_model, tags)
            logits = self.t1_head(self.dropout(output["cls"]))
            output["t1_logits"] = logits
            if tags is not None:
                if t1_targets is None or t1_mask is None:
                    raise ValueError("T1 supervision requires explicit manifest-based mask")
                if bool(t1_mask.any()):
                    t1_loss = nn.functional.cross_entropy(logits[t1_mask], t1_targets[t1_mask])
                else:
                    t1_loss = logits.sum() * 0.0
                output["t0_loss"], output["t1_loss"] = output["loss"], t1_loss
                output["loss"] = output["loss"] + self.t1_loss_weight * t1_loss
            return output
else:
    class ProposedDynamic(PhoBERTCRF):
        pass
