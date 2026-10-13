"""Linear-chain CRF with identical BIO constraints in partition, loss and decode."""

from src.modeling.labels import bio_constraints

try:
    import torch
    from torch import nn
except ImportError:
    torch = None
    nn = None


def _safe_logsumexp(values, dim):
    # Unreachable I states at t=0 must not introduce NaN gradients.
    reachable = torch.isfinite(values).any(dim=dim)
    safe = torch.where(reachable.unsqueeze(dim), values, torch.zeros_like(values))
    return torch.logsumexp(safe, dim=dim).masked_fill(~reachable, -torch.inf)


if nn is not None:
    class LinearChainCRF(nn.Module):
        def __init__(self):
            super().__init__()
            starts, transitions = bio_constraints()
            n = len(starts)
            self.start = nn.Parameter(torch.zeros(n))
            self.end = nn.Parameter(torch.zeros(n))
            self.transitions = nn.Parameter(torch.zeros(n, n))
            self.register_buffer("start_allowed", torch.tensor(starts, dtype=torch.bool))
            self.register_buffer("transition_allowed", torch.tensor(transitions, dtype=torch.bool))

        def _validate(self, emissions, mask, tags=None):
            if emissions.ndim != 3 or emissions.shape[-1] != len(self.start) or mask.shape != emissions.shape[:2]:
                raise ValueError("CRF_SHAPE_MISMATCH")
            if emissions.shape[0] == 0 or emissions.shape[1] == 0:
                raise ValueError("CRF_EMPTY_SEQUENCE_OR_BATCH")
            if mask.dtype != torch.bool or not bool(mask[:, 0].all()) or bool((~mask[:, :-1] & mask[:, 1:]).any()):
                raise ValueError("CRF_REQUIRES_NONEMPTY_CONTIGUOUS_MASK")
            if tags is not None:
                if tags.dtype != torch.long or tags.shape != mask.shape or bool(((tags < 0) | (tags >= len(self.start))).any()):
                    raise ValueError("CRF_INVALID_TAG_INDEX_INCLUDING_PADDING")
                if not bool(self.start_allowed[tags[:, 0]].all()):
                    raise ValueError("ILLEGAL_GOLD_BIO_START")
                legal = self.transition_allowed[tags[:, :-1], tags[:, 1:]]
                if bool((~legal & mask[:, 1:]).any()):
                    raise ValueError("ILLEGAL_GOLD_BIO_TRANSITION")

        def _scores(self):
            return self.start.masked_fill(~self.start_allowed, -torch.inf), self.transitions.masked_fill(~self.transition_allowed, -torch.inf)

        def log_partition(self, emissions, mask):
            self._validate(emissions, mask)
            start, transition = self._scores()
            score = start + emissions[:, 0]
            for t in range(1, emissions.shape[1]):
                proposed = _safe_logsumexp(score[:, :, None] + transition[None] + emissions[:, t, None, :], 1)
                score = torch.where(mask[:, t, None], proposed, score)
            return _safe_logsumexp(score + self.end, 1)

        def nll(self, emissions, tags, mask):
            self._validate(emissions, mask, tags)
            batch = torch.arange(emissions.shape[0], device=emissions.device)
            score = self.start[tags[:, 0]] + emissions[batch, 0, tags[:, 0]]
            for t in range(1, emissions.shape[1]):
                term = self.transitions[tags[:, t-1], tags[:, t]] + emissions[batch, t, tags[:, t]]
                score = score + torch.where(mask[:, t], term, torch.zeros_like(term))
            last = tags.gather(1, (mask.sum(1) - 1)[:, None]).squeeze(1)
            return (self.log_partition(emissions, mask) - score - self.end[last]).mean()

        def decode(self, emissions, mask, forbidden_tag_ids=None):
            self._validate(emissions, mask)
            start, transition = self._scores()
            paths = []
            for b, length in enumerate(mask.sum(1).tolist()):
                local = emissions[b, :length].clone()
                if forbidden_tag_ids:
                    local[:, forbidden_tag_ids] = -torch.inf
                score = start + local[0]
                back = []
                for row in local[1:]:
                    values, indices = (score[:, None] + transition).max(0)
                    score = values + row
                    back.append(indices)
                if not bool(torch.isfinite(score + self.end).any()):
                    raise ValueError("NO_VALID_BIO_PATH")
                path = [int((score + self.end).argmax())]
                for indices in reversed(back):
                    path.append(int(indices[path[-1]]))
                paths.append(list(reversed(path)))
            return paths
else:
    class LinearChainCRF:
        def __init__(self, *args, **kwargs):
            raise ImportError("torch required for LinearChainCRF; see docs/sprints/sprint_03/18_modeling_resource_inventory.md")
