"""PhoBERT encoder, raw-unit mean pooling, emission layer and genuine BIO CRF."""

from src.modeling.crf import LinearChainCRF, torch, nn
from src.modeling.labels import TAG_TO_ID


if nn is not None:
    class PhoBERTCRF(nn.Module):
        def __init__(self, encoder, hidden_size=None, dropout=0.1):
            super().__init__()
            self.encoder = encoder
            hidden_size = hidden_size or encoder.config.hidden_size
            self.dropout = nn.Dropout(dropout)
            self.emission = nn.Linear(hidden_size, len(TAG_TO_ID))
            self.crf = LinearChainCRF()

        def forward(self, input_ids, attention_mask, unit_to_model, tags=None):
            hidden = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
            rows = []
            for b, mapping in enumerate(unit_to_model):
                if not mapping or any(not indices for indices in mapping):
                    raise ValueError("EMPTY_PREDICTION_UNIT")
                rows.append(torch.stack([hidden[b, indices].mean(0) for indices in mapping]))
            pooled = nn.utils.rnn.pad_sequence(rows, batch_first=True)
            mask = torch.arange(pooled.shape[1], device=pooled.device)[None] < torch.tensor([len(row) for row in rows], device=pooled.device)[:, None]
            emissions = self.emission(self.dropout(pooled))
            loss = self.crf.nll(emissions, tags, mask) if tags is not None else None
            return {"emissions": emissions, "mask": mask, "cls": hidden[:, 0], "loss": loss}
else:
    class PhoBERTCRF:
        def __init__(self, *args, **kwargs):
            raise ImportError("torch required for PhoBERTCRF; neural integration is pending")
