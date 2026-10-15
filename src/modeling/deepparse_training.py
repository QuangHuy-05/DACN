"""Native Deepparse fine-tuning, fixed validation and project F1 callbacks."""

import inspect
from pathlib import Path

from src.evaluation.dev_runner import ROOT
from src.evaluation.span_features import BIO_LABELS
from src.modeling.alignment import DeepparseProcessor, encode_gold
from src.modeling.labels import DP_TAG_TO_ID


def training_pairs(rows: list[dict]) -> list[tuple[str, list[str]]]:
    processor = DeepparseProcessor()
    result = []
    for row in rows:
        alignment = processor.align_text(row["text"])
        result.append((alignment.prepared_text, encode_gold(alignment, row["spans"])))
    return result


def validate_native_api(parser_class, container_class) -> dict:
    if not hasattr(parser_class, "retrain"):
        raise RuntimeError("DEEPPARSE_RETRAIN_API_MISSING")
    constructor = inspect.signature(parser_class)
    retrain = inspect.signature(parser_class.retrain)
    container = inspect.signature(container_class)
    if not {"cache_dir", "offline", "path_to_retrained_model"} <= set(constructor.parameters):
        raise RuntimeError("DEEPPARSE_CONSTRUCTOR_API_MISMATCH; inspect pinned package before training")
    if not {"val_dataset_container", "prediction_tags", "seq2seq_params", "callbacks"} <= set(retrain.parameters):
        raise RuntimeError("DEEPPARSE_RETRAIN_API_MISMATCH")
    if not {"data", "is_training_container", "data_cleaning_pre_processing_fn"} <= set(container.parameters):
        raise RuntimeError("DEEPPARSE_CONTAINER_API_MISMATCH")
    return {"constructor": str(constructor), "retrain": str(retrain), "container": str(container)}


def construct_parser(lock: dict, device: str, checkpoint: Path | None = None):
    from deepparse.parser import AddressParser
    from deepparse.dataset_container import ListDatasetContainer
    validate_native_api(AddressParser, ListDatasetContainer)
    cache = ROOT / lock["components"]["base_checkpoint"]["path"]
    if (ROOT / lock["components"]["embedding"]["path"]).resolve() != cache.resolve():
        raise ValueError("DEEPPARSE_CHECKPOINT_EMBEDDING_MUST_SHARE_DECLARED_OFFLINE_CACHE")
    from src.modeling.resources import offline_native_resources
    with offline_native_resources():
        return AddressParser(model_type="fasttext", device=device, cache_dir=str(cache), offline=True,
                             path_to_retrained_model=str(checkpoint) if checkpoint else None, verbose=False)


def decode_native_ids(alignment, ids: list[int]) -> tuple[list, dict]:
    reverse = {index: tag for tag, index in DP_TAG_TO_ID.items()}
    if any(type(index) is not int or index not in reverse for index in ids):
        raise ValueError("UNKNOWN_NATIVE_TAG_INDEX")
    tags = [reverse[index] for index in ids]
    count = len(alignment.units)
    if "EOS" in tags[:count] or len(tags) < count:
        raise ValueError("EARLY_EOS_OR_MISSING_TAGS")
    if len(tags) > count and tags[count:] != ["EOS"]:
        raise ValueError("EXTRA_NATIVE_TAGS")
    native = list(zip(alignment.model_tokens, tags[:count]))
    spans, repairs = DeepparseProcessor().decode(alignment, native)
    return spans, {"native_tag_ids": ids, "native_tags": tags, "token_tag_pairs": native,
                   "eos_position": tags.index("EOS") if "EOS" in tags else None,
                   "eos_missing_at_output_limit": "EOS" not in tags, "illegal_bio_repairs": repairs}


def native_inference(parser, alignment):
    import torch
    if not hasattr(parser, "processor") or not hasattr(parser, "model"):
        raise RuntimeError("DEEPPARSE_PROCESSOR_API_MISMATCH")
    values = parser.processor.process_for_inference([alignment.prepared_text])
    def move(value):
        if isinstance(value, torch.Tensor):
            return value.to(parser.device)
        if isinstance(value, (list, tuple)):
            return type(value)(move(item) for item in value)
        return value
    was_training = parser.model.training
    parser.model.eval()
    try:
        with torch.no_grad():
            output = parser.model(*move(values))
        if output.ndim != 3 or output.shape[1] != 1 or output.shape[2] != len(DP_TAG_TO_ID):
            raise RuntimeError("DEEPPARSE_OUTPUT_T_B_C_API_MISMATCH")
        ids = output.argmax(2)[:, 0].cpu().tolist()
        return ids, {"log_probability": output[:, 0].cpu().tolist()}
    finally:
        parser.model.train(was_training)


def train_native(parser, splits, config: dict, logging_dir: Path, callback):
    from deepparse.dataset_container import ListDatasetContainer
    api = validate_native_api(type(parser), ListDatasetContainer)
    pairs = {split: training_pairs(rows) for split, rows in splits.items()}
    containers = {split: ListDatasetContainer(data, is_training_container=True,
                    data_cleaning_pre_processing_fn=None) for split, data in pairs.items()}
    if len(containers["train"]) != 240 or len(containers["dev"]) != 60:
        raise ValueError("FIXED_SPLIT_COUNT_MISMATCH")
    # The native method replaces only the prediction projection for 24 custom tags.
    # No seq2seq_params: pretrained encoder/decoder dimensions and weights survive.
    parser.retrain(containers["train"], val_dataset_container=containers["dev"],
        batch_size=config["effective_batch_size"], epochs=config["max_epochs"], num_workers=0,
        learning_rate=config["candidate"]["learning_rate"], prediction_tags=DP_TAG_TO_ID,
        seq2seq_params=None, callbacks=[callback], seed=config["seed"],
        logging_path=str(logging_dir), disable_tensorboard=True, verbose=False)
    return api
