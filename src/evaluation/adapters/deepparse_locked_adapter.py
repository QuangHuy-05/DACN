"""Zero-shot native FastText loader gated by real local resources and host capacity."""

from pathlib import Path

from src.evaluation.adapters.deepparse_adapter import DeepparseFastTextAdapter
from src.evaluation.dev_runner import ROOT
from src.modeling.protocol import load_config
from src.modeling.resources import preflight, validate_resource_lock


def zero_shot_gate(resource_lock_path):
    path = Path(resource_lock_path)
    path = path if path.is_absolute() else ROOT / path
    config = load_config(ROOT / "configs/modeling/sprint03/dp_ft_ft_v1.json")
    readiness = preflight(config, path)
    if readiness["blockers"]:
        raise RuntimeError("DP_ZS_RESOURCE_GATE:" + str(readiness["blockers"]))
    return path, validate_resource_lock(path, "DP-FT-FT")


class LockedDeepparseFastTextAdapter(DeepparseFastTextAdapter):
    def __init__(self, resource_lock_path):
        _, lock = zero_shot_gate(resource_lock_path)
        from src.modeling.deepparse_training import construct_parser
        # None selects the native pretrained checkpoint, never fine-tuned weights.
        self.parser = construct_parser(lock, "cpu", checkpoint=None)
