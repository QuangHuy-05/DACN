"""Read-only diagnostics for existing code tables, never legal code promotion."""

from collections import Counter, defaultdict
import csv
from difflib import SequenceMatcher
import json
from pathlib import Path
import unicodedata

from src.data.administrative_code_verifier import canonical_name, TemporalGazetteerEvidence
from src.evaluation.dev_runner import file_hash, write_json, write_jsonl


def accent_fold(value):
    return ''.join(char for char in unicodedata.normalize('NFD', value.casefold())
                   if not unicodedata.combining(char)).replace('đ', 'd')


def diagnostic_difference(canonical, raw, audited_aliases=()):
    """Folded names describe differences only; they are not lookup evidence."""
    if canonical == raw:
        return 'IDENTICAL'
    if canonical_name(canonical) == canonical_name(raw):
        return 'NORMALIZED_ONLY'
    if canonical_name(raw) in {canonical_name(item) for item in audited_aliases}:
        return 'EXISTING_AUDITED_ALIAS'
    if accent_fold(canonical) == accent_fold(raw):
        return 'DIACRITIC_OR_TONE_VARIATION'
    prefixes = ('Thành phố ', 'Thị trấn ', 'Thị xã ', 'Phường ', 'Huyện ', 'Quận ', 'Tỉnh ', 'Xã ')
    def split_name(value):
        prefix = next((prefix for prefix in prefixes if value.startswith(prefix)), '')
        return prefix.strip(), value[len(prefix):]
    left, right = split_name(canonical), split_name(raw)
    if left[0] != right[0] and accent_fold(left[1]) == accent_fold(right[1]):
        return 'UNIT_TYPE_MISMATCH'
    return 'NAME_MISMATCH_UNAUDITED'


def csv_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def reconcile_existing(root, output):
    if output.exists():
        raise FileExistsError(output)
    gazetteer = TemporalGazetteerEvidence(root / 'data/processed/gazetteer/s3_v2')
    raw_paths = {level: root / f'third_party/vietnamadminunits/data/raw/danhmuchanhchinh.gso.gov.vn_{level}_2025-07-18.csv'
                 for level in ('ward', 'district')}
    indices = {level: defaultdict(list) for level in raw_paths}
    codes = {level: defaultdict(list) for level in raw_paths}
    leaf_names = {level: defaultdict(list) for level in raw_paths}
    source_files = []
    for level, path in raw_paths.items():
        columns, rows = csv_rows(path)
        required = {'Mã', 'Tên', 'Cấp', 'Tỉnh / Thành Phố'} | ({'Quận Huyện'} if level == 'ward' else set())
        if not required <= set(columns):
            raise ValueError('RAW_SOURCE_SCHEMA_MISMATCH:' + level)
        source_id = 'existing_gso_raw_' + level
        digest = file_hash(path)
        source_files.append({'source_id': source_id, 'path': path.relative_to(root).as_posix(), 'sha256': digest,
                             'bytes': path.stat().st_size, 'row_count': len(rows), 'columns': columns,
                             'encoding': 'UTF-8-sig' if path.read_bytes().startswith(b'\xef\xbb\xbf') else 'UTF-8',
                             'filename_date': '2025-07-18', 'snapshot_date_proven': False})
        for number, row in enumerate(rows, 2):
            if level == 'ward' and row['Cấp'] not in ('Phường', 'Xã', 'Thị trấn'):
                continue
            key = tuple(canonical_name(row[name]) for name in
                        (('Tỉnh / Thành Phố', 'Quận Huyện', 'Tên') if level == 'ward' else ('Tỉnh / Thành Phố', 'Tên')))
            candidate = {'full_key': list(key), 'code': row['Mã'], 'source_level': row['Cấp'],
                         'source_id': source_id, 'source_locator': f'CSV record {number - 1} (header excluded)',
                         'source_row_with_header': number, 'source_sha256': digest}
            indices[level][key].append(candidate)
            codes[level][row['Mã']].append(candidate)
            leaf_names[level][key[-1]].append(candidate)
    aliases = defaultdict(list)
    _, alias_rows = csv_rows(root / 'data/processed/gazetteer/s3_v2/aliases.csv')
    for row in alias_rows:
        aliases[row['entity_id']].append(row['alias'])
    counts, decisions, all_rows = {level: Counter() for level in raw_paths}, [], []
    for entity in gazetteer.entities:
        level = entity['level']
        if entity['system'] != 'cu' or level not in indices:
            continue
        full = gazetteer.full_key(entity)
        key = full[2:] if level == 'ward' else full[2:4]
        exact = indices[level].get(key, [])
        code_set = {row['code'] for row in exact}
        stored = entity['candidate_code'] or entity['official_code']
        status = ('EXACT_KEY_AND_CODE_MATCH' if len(code_set) == 1 and stored in code_set else
                  'EXACT_KEY_FOUND_STORED_CODE_MISSING' if len(code_set) == 1 and not stored else
                  'CODE_CONFLICT_OR_AMBIGUITY' if exact else 'NO_EXACT_KEY')
        counts[level][status] += 1
        base = {'entity_id': entity['entity_id'], 'system': 'cu', 'level': level, 'gazetteer_key': list(key),
                'stored_code': stored or None, 'exact_status': status, 'official_verified': False,
                'reference_period_status': 'UNVERIFIED_EXPORT_QUERY', 'license_status': 'UNKNOWN_DATA_REUSE',
                'reason': 'Internal source agreement does not establish a dated official identity.'}
        all_rows.append({**base, 'exact_raw_candidates': exact})
        if status == 'EXACT_KEY_AND_CODE_MATCH':
            continue
        candidates = exact or codes[level].get(stored, []) or leaf_names[level].get(key[-1], [])
        method = 'exact_full_key' if exact else 'existing_candidate_code' if codes[level].get(stored, []) else 'exact_leaf_name'
        hierarchy, current = {}, entity
        while current:
            hierarchy[current['level']] = current
            current = gazetteer.by_id.get(current['parent_id'])
        component_levels = ['province', 'district', 'ward'] if level == 'ward' else ['province', 'district']
        details = []
        for candidate in candidates:
            comparisons = [{'level': part, 'canonical': left, 'raw': right,
                            'difference': diagnostic_difference(left, right, aliases[hierarchy[part]['entity_id']])}
                           for part, left, right in zip(component_levels, key, candidate['full_key'])]
            details.append({**candidate, 'component_differences': comparisons, 'not_identity_verification': True})
        differences = {item['difference'] for row in details for item in row['component_differences']} - {'IDENTICAL'}
        if status == 'EXACT_KEY_FOUND_STORED_CODE_MISSING':
            category = 'CODE_ABSENT_EXACT_RAW_CANDIDATE'
        elif not details:
            category = 'NO_RAW_CANDIDATE_BY_CODE_OR_EXACT_NAME'
        elif len(details) > 1:
            category = 'MULTIPLE_RAW_CANDIDATES'
        elif differences <= {'DIACRITIC_OR_TONE_VARIATION', 'NORMALIZED_ONLY'}:
            category = 'ORTHOGRAPHIC_VARIATION_NOT_AUTHORIZED_ALIAS'
        elif 'UNIT_TYPE_MISMATCH' in differences:
            category = 'UNIT_TYPE_OR_PERIOD_MISMATCH'
        elif differences <= {'EXISTING_AUDITED_ALIAS', 'NORMALIZED_ONLY'}:
            category = 'EXISTING_AUDITED_ALIAS_CORROBORATED_DATE_PENDING'
        else:
            category = 'NAME_OR_PARENT_MISMATCH_NEEDS_DATED_EVIDENCE'
        decisions.append({**base, 'category': category, 'candidate_method': method,
                          'raw_candidates': details, 'candidate_count': len(details),
                          'decision': 'UNRESOLVED_AUTHORITY_OR_PERIOD',
                          'required_evidence': 'original dated portal export/query or official dated catalogue with full parents',
                          'rule': 'no fuzzy promotion; no code filling; derivative diagnostics only'})
    expected = {'ward': {'EXACT_KEY_AND_CODE_MATCH': 9451, 'NO_EXACT_KEY': 584},
                'district': {'EXACT_KEY_AND_CODE_MATCH': 665, 'EXACT_KEY_FOUND_STORED_CODE_MISSING': 5, 'NO_EXACT_KEY': 26}}
    if {level: dict(values) for level, values in counts.items()} != expected or len(decisions) != 615:
        raise ValueError('BASELINE_RECONCILIATION_COUNTS_DRIFT:' + repr(counts))
    output.mkdir(parents=True)
    write_jsonl(output / 'full_reconciliation.jsonl', all_rows)
    write_jsonl(output / 'reconciliation_615.jsonl', decisions)
    write_jsonl(output / 'unresolved_review_queue.jsonl', decisions)
    with (output / 'reconciliation_615.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        fields = ['entity_id', 'level', 'gazetteer_key', 'stored_code', 'exact_status', 'category', 'candidate_method',
                  'candidate_count', 'raw_candidates', 'decision', 'reason', 'required_evidence']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in decisions:
            writer.writerow({key: json.dumps(row[key], ensure_ascii=False) if isinstance(row[key], (list, dict)) else row[key] for key in fields})
    summary = {'status': 'AUDIT_COMPLETE_PROVENANCE_AND_PERIOD_UNRESOLVED',
               'baseline_counts': expected, 'review_cases': len(decisions), 'category_counts': dict(Counter(row['category'] for row in decisions)),
               'newly_verified_official_codes': 0, 'new_package_released': False,
               'source_files': source_files, 'frozen_manifest_sha256': file_hash(gazetteer.directory / 'manifest.json'),
               'output_sha256': {path.name: file_hash(path) for path in output.iterdir() if path.is_file()}}
    write_json(output / 'summary.json', summary)
    return summary
