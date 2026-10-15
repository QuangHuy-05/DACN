# Corpus Sprint 3

240 train / 60 dev / 100 test. Train/dev bytes match corpus_train_dev_v2; its source manifest remains immutable.

Test annotation: AI-assisted human review; independent agreement NOT_MEASURED. Read evaluation_exclusions.t1 before T1 scoring/structure diagnostics; every T0 span remains.

Training uses the original pinned train/dev release. Final inference uses test_input.jsonl only; gold is opened by a separate scorer after prediction freeze. Test is never for tuning.
