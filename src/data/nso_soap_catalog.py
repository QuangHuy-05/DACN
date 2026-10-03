"""Read-only client and parser for the NSO administrative catalogue SOAP service.

Service: https://danhmuchanhchinh.nso.gov.vn/DMDVHC.asmx (namespace http://tempuri.org/).
Only the three read operations ``DanhMucTinh``, ``DanhMucQuanHuyen`` and
``DanhMucPhuongXa`` are allowed; no update request is ever sent.

Evidence policy:
- every raw response is stored byte-for-byte together with the request body;
- codes are kept as strings (leading zeros preserved, never re-padded);
- only ``TABLE`` rows inside the diffgram are data; ``xs:element`` schema nodes
  are ignored;
- a query date proves the state of the catalogue *as of* that date only. It is
  not a legal ``valid_from``.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import unicodedata
import urllib.error
import urllib.request
from xml.etree import ElementTree
from xml.sax.saxutils import escape

SERVICE_URL = "https://danhmuchanhchinh.nso.gov.vn/DMDVHC.asmx"
NAMESPACE = "http://tempuri.org/"
SOAP_ENV = "http://schemas.xmlsoap.org/soap/envelope/"
DIFFGRAM_NS = "urn:schemas-microsoft-com:xml-diffgram-v1"
MSDATA_NS = "urn:schemas-microsoft-com:xml-msdata"
LICENSE_STATUS = "PUBLIC_PORTAL_TERMS_NOT_LOCATED"
MAX_RESPONSE_BYTES = 64 * 1024 * 1024

OPERATIONS = {
    "DanhMucTinh": {"params": ("DenNgay",), "level": "province",
                    "required": ("MaTinh", "TenTinh"), "code": "MaTinh", "code_len": 2},
    "DanhMucQuanHuyen": {"params": ("DenNgay", "Tinh", "TenTinh"), "level": "district",
                         "required": ("MaTinh", "TenTinh", "MaQuanHuyen", "TenQuanHuyen"),
                         "code": "MaQuanHuyen", "code_len": 3},
    "DanhMucPhuongXa": {"params": ("DenNgay", "Tinh", "TenTinh", "QuanHuyen", "TenQuanHuyen"), "level": "ward",
                        "required": ("MaTinh", "TenTinh", "MaPhuongXa", "TenPhuongXa"),
                        "code": "MaPhuongXa", "code_len": 5},
}


class NsoSoapError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def nfc(value: str | None) -> str:
    return " ".join(unicodedata.normalize("NFC", value or "").split())


def build_envelope(operation: str, params: dict[str, str]) -> bytes:
    if operation not in OPERATIONS:
        raise ValueError("UNSUPPORTED_OPERATION:" + operation)
    allowed = OPERATIONS[operation]["params"]
    unknown = set(params) - set(allowed)
    if unknown:
        raise ValueError("UNKNOWN_PARAMETERS:" + ",".join(sorted(unknown)))
    if "DenNgay" not in params:
        raise ValueError("DENNGAY_REQUIRED")
    datetime.strptime(params["DenNgay"], "%d/%m/%Y")
    inner = "".join(f"<{name}>{escape(params.get(name, ''))}</{name}>" for name in allowed)
    body = ('<?xml version="1.0" encoding="utf-8"?>'
            f'<soap:Envelope xmlns:soap="{SOAP_ENV}"><soap:Body>'
            f'<{operation} xmlns="{NAMESPACE}">{inner}</{operation}>'
            '</soap:Body></soap:Envelope>')
    return body.encode("utf-8")


def post_soap(operation: str, params: dict[str, str], timeout: int = 30, retries: int = 2,
              max_bytes: int = MAX_RESPONSE_BYTES, opener=urllib.request.urlopen) -> dict:
    """POST one read request; bounded timeout/retry/size. Returns bytes + HTTP evidence."""
    body = build_envelope(operation, params)
    headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": f'"{NAMESPACE}{operation}"'}
    attempts = []
    for attempt in range(1, retries + 1):
        started = datetime.now(timezone.utc).astimezone()
        try:
            request = urllib.request.Request(SERVICE_URL, data=body, method="POST", headers=headers)
            with opener(request, timeout=timeout) as response:
                data = response.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise NsoSoapError("RESPONSE_TOO_LARGE")
                return {"request_body": body, "request_headers": headers, "response": data,
                        "http_status": response.status, "content_type": response.headers.get("Content-Type"),
                        "retrieved_at": started.isoformat(), "attempts": attempts + [{"attempt": attempt, "status": response.status}]}
        except urllib.error.HTTPError as error:
            payload = error.read(max_bytes)
            attempts.append({"attempt": attempt, "status": error.code, "error": "HTTPError"})
            if b"Fault" in payload:
                raise NsoSoapError("SOAP_FAULT_HTTP_%d:%s" % (error.code, payload[:500].decode("utf-8", "replace")))
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            attempts.append({"attempt": attempt, "error": type(error).__name__, "detail": str(error)[:200]})
        time.sleep(min(2 ** attempt, 10))
    raise NsoSoapError("REQUEST_FAILED_AFTER_RETRIES:" + json.dumps(attempts))


def parse_table_rows(data: bytes, operation: str) -> list[dict]:
    """Parse diffgram ``TABLE`` rows; raise on SOAP Fault/empty/schema problems."""
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as error:
        raise NsoSoapError("XML_PARSE_ERROR:" + str(error))
    if root.find(f".//{{{SOAP_ENV}}}Fault") is not None:
        raise NsoSoapError("SOAP_FAULT")
    result = root.find(f".//{{{NAMESPACE}}}{operation}Result")
    if result is None:
        raise NsoSoapError("RESULT_ELEMENT_MISSING")
    diffgram = result.find(f"{{{DIFFGRAM_NS}}}diffgram")
    if diffgram is None:
        raise NsoSoapError("DIFFGRAM_MISSING")
    rows = []
    # DataSet rows have no namespace (xmlns=""); schema xs:element nodes are skipped.
    for index, element in enumerate(diffgram.iter("TABLE")):
        row = {child.tag: (child.text or "") for child in element}
        row["_diffgr_id"] = element.get(f"{{{DIFFGRAM_NS}}}id") or ""
        row["_row_order"] = element.get(f"{{{MSDATA_NS}}}rowOrder") or str(index)
        rows.append(row)
    return rows


def validate_rows(rows: list[dict], operation: str) -> dict:
    spec = OPERATIONS[operation]
    issues = []
    if not rows:
        issues.append("EMPTY_RESPONSE")
    for row in rows:
        for field in spec["required"]:
            if not row.get(field, "").strip():
                issues.append(f"MISSING_FIELD:{field}:{row['_diffgr_id']}")
        for field, length in (("MaTinh", 2), ("MaQuanHuyen", 3), ("MaPhuongXa", 5)):
            value = row.get(field)
            if value is None or value == "":
                continue
            if not (value.isascii() and value.isdigit() and len(value) == length):
                issues.append(f"CODE_FORMAT:{field}={value!r}:{row['_diffgr_id']}")
    codes = Counter(row.get(spec["code"]) for row in rows)
    duplicates = sorted(code for code, count in codes.items() if count > 1)
    if duplicates:
        issues.append("DUPLICATE_CODES:" + ",".join(duplicates[:20]))
    return {"rows": len(rows), "issues": issues, "duplicate_codes": duplicates,
            "status": "PASS" if not issues else "FAIL"}


def save_response(output_dir: Path, name: str, operation: str, params: dict, fetched: dict, scope: str) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    xml_path, request_path = output_dir / f"{name}.xml", output_dir / f"{name}.request.xml"
    for path in (xml_path, request_path):
        if path.exists():
            raise FileExistsError(path)
    xml_path.write_bytes(fetched["response"])
    request_path.write_bytes(fetched["request_body"])
    return {"name": name, "source_url": SERVICE_URL, "operation": operation,
            "soap_action": fetched["request_headers"]["SOAPAction"], "query": params, "scope": scope,
            "filters": {key: value for key, value in params.items() if key != "DenNgay" and value},
            "retrieved_at": fetched["retrieved_at"], "http_status": fetched["http_status"],
            "content_type": fetched["content_type"], "attempts": fetched["attempts"],
            "response_file": xml_path.name, "bytes": len(fetched["response"]),
            "sha256": sha256_bytes(fetched["response"]), "request_file": request_path.name,
            "request_sha256": sha256_bytes(fetched["request_body"]), "license_status": LICENSE_STATUS}


def iso_to_vn(iso_date: str) -> str:
    return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d/%m/%Y")


def build_reference(responses: dict[str, tuple[dict, list[dict]]], as_of: str, system: str) -> tuple[list[dict], dict]:
    """Build canonical reference rows for one as-of date from province/district/ward responses.

    ``responses`` maps level -> (download manifest entry, parsed rows).
    Returns (reference rows, validation report). Parent links are verified by code.
    """
    reference, issues = [], []
    provinces = {}
    districts = {}
    for level, operation in (("province", "DanhMucTinh"), ("district", "DanhMucQuanHuyen"), ("ward", "DanhMucPhuongXa")):
        if level not in responses:
            continue
        entry, rows = responses[level]
        for row in rows:
            province_code, province_name = row.get("MaTinh", ""), nfc(row.get("TenTinh"))
            district_code, district_name = row.get("MaQuanHuyen", ""), nfc(row.get("TenQuanHuyen"))
            if level == "province":
                code, name = province_code, province_name
                provinces[code] = name
                parent_ok = True
            elif level == "district":
                code, name = district_code, district_name
                parent_ok = provinces.get(province_code) == province_name
                if parent_ok:
                    districts[code] = (name, province_code)
            else:
                code, name = row.get("MaPhuongXa", ""), nfc(row.get("TenPhuongXa"))
                parent_ok = provinces.get(province_code) == province_name and (
                    bool(district_code) and districts.get(district_code) == (district_name, province_code)
                    if system == "cu" else not district_code)
            if not parent_ok:
                issues.append(f"PARENT_LINK_MISMATCH:{level}:{code}:{row['_diffgr_id']}")
            reference.append({
                "level": level, "system": system, "official_name": name, "official_code": code,
                "province_code": province_code if level != "province" else "",
                "province_name": province_name if level != "province" else "",
                "district_code": district_code if level == "ward" else "",
                "district_name": district_name if level == "ward" else "",
                "unit_type": nfc(row.get("LoaiHinh")), "as_of_date": as_of,
                "source_id": f"nso_soap_{operation}_{as_of}", "source_hash": entry["sha256"],
                "source_file": entry["response_file"],
                "source_locator": f"{entry['response_file']}#TABLE[diffgr:id={row['_diffgr_id']}]",
                "extraction_status": "PARSED_DIFFGRAM_TABLE_ROW",
                "validation_status": "PARENT_CODE_LINK_PASS" if parent_ok else "PARENT_CODE_LINK_FAIL",
            })
    counts = Counter(row["level"] for row in reference)
    keys = Counter((row["level"], row["province_name"], row["district_name"], row["official_name"]) for row in reference)
    duplicate_keys = [list(key) for key, count in keys.items() if count > 1]
    level_codes = Counter((row["level"], row["official_code"]) for row in reference)
    duplicate_codes = [list(key) for key, count in level_codes.items() if count > 1]
    return reference, {"as_of_date": as_of, "system": system, "counts": dict(counts),
                       "parent_link_issues": issues, "duplicate_full_keys": duplicate_keys,
                       "duplicate_level_codes": duplicate_codes,
                       "status": "FAIL" if duplicate_codes or duplicate_keys else "PARTIAL_PARENT_LINK_GAPS" if issues else "PASS",
                       "temporal_semantics": "as_of snapshot only; not a legal valid_from/valid_to interval"}


def province_counts(reference: list[dict], level: str) -> dict:
    counter = defaultdict(int)
    for row in reference:
        if row["level"] == level:
            counter[row["province_name"]] += 1
    return dict(sorted(counter.items()))
