from datetime import datetime, timezone
import hashlib
import unicodedata
import osmium
import pandas as pd
from tqdm import tqdm

CUTOFF_TIME = datetime(2025, 6, 30, 23, 59, 59, tzinfo=timezone.utc)


def clean_tag(value):
    """Reject non-Latin writing systems and control characters; retain Vietnamese."""
    value = unicodedata.normalize("NFC", str(value or "")).strip(" ,")
    if not value or ",," in value:
        return ""
    for char in value:
        category = unicodedata.category(char)
        if category.startswith("L") and "LATIN" in unicodedata.name(char, ""):
            continue
        if "0" <= char <= "9" or char in " /.,-()_\t":
            continue
        if category.startswith("M"):  # Vietnamese combining marks after NFC.
            continue
        else:
            return ""
    return value

class HistoryBiDirectionalMapper(osmium.SimpleHandler):
    def __init__(self):
        super(HistoryBiDirectionalMapper, self).__init__()
        self.history_tracker = {}
        self.pbar = tqdm(desc="Đang quét toàn bộ lịch sử OSM", unit=" revisions", mininterval=5)

    def parse_tags(self, tags, geometry_signature=""):
        street = clean_tag(tags.get('addr:street', ''))
        if not street or street.lower() in ['không tên', 'unnamed', 'đang cập nhật']:
            return None

        housenumber = clean_tag(tags.get('addr:housenumber', ''))
        ward = clean_tag(tags.get('addr:ward', '')) or clean_tag(tags.get('addr:subdistrict', ''))
        district = clean_tag(tags.get('addr:district', ''))
        city = clean_tag(tags.get('addr:city', '')) or clean_tag(tags.get('addr:province', ''))

        if not (city or district or ward):
            return None

        # Any rejected nonempty administrative tag invalidates the address.
        for tag_name in ('addr:housenumber', 'addr:ward', 'addr:subdistrict', 'addr:district', 'addr:city', 'addr:province'):
            if tags.get(tag_name, '') and not clean_tag(tags.get(tag_name, '')):
                return None

        full_addr = ", ".join([c for c in [housenumber, street, ward, district, city] if c])
        return {
            'housenumber': housenumber,
            'street': street,
            'ward': ward,
            'district': district,
            'city': city,
            'full_address': full_addr,
            'geometry_signature': geometry_signature,
        }

    @staticmethod
    def geometry_signature(elem, elem_type):
        """Return a compact geometry fingerprint for movement diagnostics.

        Nodes retain a rounded coordinate. Ways retain a SHA-256 digest of the
        ordered node references. The fingerprint only says that geometry was
        edited; it does not by itself prove an administrative boundary change.
        """
        if elem_type == 'node':
            try:
                if elem.location.valid():
                    return f"node:{elem.location.lat:.7f},{elem.location.lon:.7f}"
            except (AttributeError, RuntimeError):
                return ""
            return ""
        if elem_type == 'way':
            try:
                refs = ",".join(str(node.ref) for node in elem.nodes)
            except AttributeError:
                return ""
            if refs:
                return f"way:{hashlib.sha256(refs.encode('utf-8')).hexdigest()}"
        return ""

    def process_element(self, elem, elem_type):
        self.pbar.update(1)
        key = (elem_type, elem.id)

        # A history extract contains many large, non-address ways.  Build a
        # geometry fingerprint only after tags pass address validation; doing
        # it beforehand can spend most of the run hashing irrelevant geometry.
        parsed = self.parse_tags(elem.tags) if elem.visible else None
        if parsed is not None:
            parsed["geometry_signature"] = self.geometry_signature(elem, elem_type)
        if key not in self.history_tracker:
            if parsed is None:
                return
            self.history_tracker[key] = {'old': None, 'new': None, 'has_post_cutoff_revision': False}
        if elem.timestamp <= CUTOFF_TIME:
            self.history_tracker[key]['old'] = parsed
        else:
            self.history_tracker[key]['has_post_cutoff_revision'] = True
            self.history_tracker[key]['new'] = parsed

    def node(self, n):
        self.process_element(n, 'node')

    def way(self, w):
        self.process_element(w, 'way')


def balance_dataframe_by_region(df, region_col='VungMien', samples_per_region=None, random_state=42):
    if df.empty:
        return df

    groups = df.groupby(region_col)
    min_count = groups.size().min()
    target_count = samples_per_region if samples_per_region else max(min_count, 100)

    balanced_list = []
    for _, group in groups:
        if len(group) <= target_count:
            balanced_list.append(group)
        else:
            balanced_list.append(group.sample(n=target_count, random_state=random_state))

    return pd.concat(balanced_list).sample(frac=1.0, random_state=random_state).reset_index(drop=True)
