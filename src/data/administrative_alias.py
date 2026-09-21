"""Controlled administrative aliases and typographical corrections for OSM diffs.

This module provides an explicit, auditable lookup table to resolve known
spelling variants, abbreviations, and missing administrative prefixes in
crowdsourced OpenStreetMap address tags without guessing unseen territorial edges.
"""

from __future__ import annotations

import re
from typing import Any

from src.data.administrative_mapping import clean_value, normalise_text


# Verified province aliases: foreign language names, missing accents, and colloquial abbreviations
PROVINCE_ALIASES: dict[str, str] = {
    "ho chi minh city": "Thành phố Hồ Chí Minh",
    "hồ chí minh city": "Thành phố Hồ Chí Minh",
    "tp. hồ chí minh": "Thành phố Hồ Chí Minh",
    "tp hồ chí minh": "Thành phố Hồ Chí Minh",
    "hồ chí minh": "Thành phố Hồ Chí Minh",
    "hcm": "Thành phố Hồ Chí Minh",
    "tphcm": "Thành phố Hồ Chí Minh",
    "hanoi": "Thành phố Hà Nội",
    "ha noi": "Thành phố Hà Nội",
    "thành phố hà nội": "Thành phố Hà Nội",
    "hà nội": "Thành phố Hà Nội",
    "hai phong": "Thành phố Hải Phòng",
    "haiphong": "Thành phố Hải Phòng",
    "thành phố hải phòng": "Thành phố Hải Phòng",
    "đà nẵng": "Thành phố Đà Nẵng",
    "da nang": "Thành phố Đà Nẵng",
    "thành phố đà nẵng": "Thành phố Đà Nẵng",
    "cần thơ": "Thành phố Cần Thơ",
    "can tho": "Thành phố Cần Thơ",
    "thành phố cần thơ": "Thành phố Cần Thơ",
    "bac ninh": "Tỉnh Bắc Ninh",
    "bắc ninh": "Tỉnh Bắc Ninh",
    "tỉnh bắc ninh": "Tỉnh Bắc Ninh",
    "thành phố bắc ninh": "Tỉnh Bắc Ninh",
    "bac giang": "Tỉnh Bắc Giang",
    "bắc giang": "Tỉnh Bắc Giang",
    "tỉnh bắc giang": "Tỉnh Bắc Giang",
    "thanh hóa": "Tỉnh Thanh Hóa",
    "thanh hoa": "Tỉnh Thanh Hóa",
    "tỉnh thanh hóa": "Tỉnh Thanh Hóa",
    "vĩnh long": "Tỉnh Vĩnh Long",
    "vinh long": "Tỉnh Vĩnh Long",
    "tỉnh vĩnh long": "Tỉnh Vĩnh Long",
    "lâm đồng": "Tỉnh Lâm Đồng",
    "lam dong": "Tỉnh Lâm Đồng",
    "tỉnh lâm đồng": "Tỉnh Lâm Đồng",
    "thành phố đà lạt": "Tỉnh Lâm Đồng",
    "gia lai": "Tỉnh Gia Lai",
    "tỉnh gia lai": "Tỉnh Gia Lai",
    "đồng nai": "Tỉnh Đồng Nai",
    "dong nai": "Tỉnh Đồng Nai",
    "tỉnh đồng nai": "Tỉnh Đồng Nai",
    "thành phố biên hòa": "Tỉnh Đồng Nai",
    "tỉnh hưng yên": "Tỉnh Hưng Yên",
    "hưng yên": "Tỉnh Hưng Yên",
    "quảng trị": "Tỉnh Quảng Trị",
    "quang tri": "Tỉnh Quảng Trị",
    "quảng nam": "Tỉnh Quảng Nam",
    "thừa thiên huế": "Thành phố Huế",
    "thừa thiên - huế": "Thành phố Huế",
    "huế": "Thành phố Huế",
}

# Verified district aliases: typos, missing 'Quận/Huyện' prefix, and numeric formats
DISTRICT_ALIASES: dict[str, str] = {
    "thành phố bác ninh": "Thành phố Bắc Ninh",
    "q.ba đình": "Quận Ba Đình",
    "ba đình": "Quận Ba Đình",
    "quận ba đình": "Quận Ba Đình",
    "hoàn kiếm": "Quận Hoàn Kiếm",
    "quận hoàn kiếm": "Quận Hoàn Kiếm",
    "hoan kiem": "Quận Hoàn Kiếm",
    "quận hoan kiem": "Quận Hoàn Kiếm",
    "đống đa": "Quận Đống Đa",
    "dong da": "Quận Đống Đa",
    "quận đống đa": "Quận Đống Đa",
    "tây hồ": "Quận Tây Hồ",
    "tay ho": "Quận Tây Hồ",
    "quận tây hồ": "Quận Tây Hồ",
    "quận tay ho": "Quận Tây Hồ",
    "bắc từ liêm": "Quận Bắc Từ Liêm",
    "quận bắc từ liêm": "Quận Bắc Từ Liêm",
    "hà đông": "Quận Hà Đông",
    "quận hà đông": "Quận Hà Đông",
    "hoàng mai": "Quận Hoàng Mai",
    "quận hoàng mai": "Quận Hoàng Mai",
    "long biên": "Quận Long Biên",
    "quận long biên": "Quận Long Biên",
    "gia lâm": "Huyện Gia Lâm",
    "huyện gia lâm": "Huyện Gia Lâm",
    "việt yên": "Thị xã Việt Yên",
    "huyện việt yên": "Thị xã Việt Yên",
    "thị xã việt yên": "Thị xã Việt Yên",
    "phú nhuận": "Quận Phú Nhuận",
    "quận phú nhuận": "Quận Phú Nhuận",
    "bình thạnh": "Quận Bình Thạnh",
    "quận bình thạnh": "Quận Bình Thạnh",
    "bình tân": "Quận Bình Tân",
    "quận bình tân": "Quận Bình Tân",
    "bình chánh": "Huyện Bình Chánh",
    "huyện bình chánh": "Huyện Bình Chánh",
    "tân bình": "Quận Tân Bình",
    "quận tân bình": "Quận Tân Bình",
    "gò vấp": "Quận Gò Vấp",
    "quận gò vấp": "Quận Gò Vấp",
    "quận 3": "Quận 3",
    "quan 3": "Quận 3",
    "3": "Quận 3",
    "quận 6": "Quận 6",
    "quan 6": "Quận 6",
    "6": "Quận 6",
    "quận 10": "Quận 10",
    "quan 10": "Quận 10",
    "10": "Quận 10",
    "quận 11": "Quận 11",
    "quan 11": "Quận 11",
    "11": "Quận 11",
    "quận 2": "Thành phố Thủ Đức",
    "quan 2": "Thành phố Thủ Đức",
    "2": "Thành phố Thủ Đức",
    "thành phố thủ đức": "Thành phố Thủ Đức",
    "thành phố từ sơn": "Thành phố Từ Sơn",
    "từ sơn": "Thành phố Từ Sơn",
    "huyện gia bình": "Huyện Gia Bình",
    "gia bình": "Huyện Gia Bình",
    "huyện tiên du": "Huyện Tiên Du",
    "tiên du": "Huyện Tiên Du",
    "thị xã quế võ": "Thị xã Quế Võ",
    "quế võ": "Thị xã Quế Võ",
    "huyện thuận thành": "Thị xã Thuận Thành",
    "thuận thành": "Thị xã Thuận Thành",
    "huyện hiệp hòa": "Huyện Hiệp Hòa",
    "hiệp hòa": "Huyện Hiệp Hòa",
    "chư sê": "Huyện Chư Sê",
    "huyện chư sê": "Huyện Chư Sê",
    "long hồ": "Huyện Long Hồ",
    "huyện long hồ": "Huyện Long Hồ",
}

# Verified ward aliases: unaccented forms and missing 'Phường/Xã/Thị trấn' prefixes
WARD_ALIASES: dict[str, str] = {
    "vũ ninh": "Phường Vũ Ninh",
    "phường vũ ninh": "Phường Vũ Ninh",
    "hàng buồm": "Phường Hàng Buồm",
    "hang buom": "Phường Hàng Buồm",
    "hang buồm": "Phường Hàng Buồm",
    "phường hàng buồm": "Phường Hàng Buồm",
    "hàng bông": "Phường Hàng Bông",
    "phường hàng bông": "Phường Hàng Bông",
    "hàng bạc": "Phường Hàng Bạc",
    "phường hàng bạc": "Phường Hàng Bạc",
    "hàng bồ": "Phường Hàng Bồ",
    "hang bo": "Phường Hàng Bồ",
    "phường hàng bồ": "Phường Hàng Bồ",
    "hàng mã": "Phường Hàng Mã",
    "phường hàng mã": "Phường Hàng Mã",
    "hàng gai": "Phường Hàng Gai",
    "hang gai": "Phường Hàng Gai",
    "phường hàng gai": "Phường Hàng Gai",
    "hàng trống": "Phường Hàng Trống",
    "phường hàng trống": "Phường Hàng Trống",
    "đồng xuân": "Phường Đồng Xuân",
    "phường đồng xuân": "Phường Đồng Xuân",
    "cửa nam": "Phường Cửa Nam",
    "phường cửa nam": "Phường Cửa Nam",
    "cửa đông": "Phường Cửa Đông",
    "phường cửa đông": "Phường Cửa Đông",
    "điện biên": "Phường Điện Biên",
    "phường điện biên": "Phường Điện Biên",
    "trúc bạch": "Phường Trúc Bạch",
    "phường trúc bạch": "Phường Trúc Bạch",
    "quán thánh": "Phường Quán Thánh",
    "phường quán thánh": "Phường Quán Thánh",
    "ngọc hà": "Phường Ngọc Hà",
    "phường ngọc hà": "Phường Ngọc Hà",
    "kim mã": "Phường Kim Mã",
    "phường kim mã": "Phường Kim Mã",
    "nguyễn trung trực": "Phường Nguyễn Trung Trực",
    "phường nguyễn trung trực": "Phường Nguyễn Trung Trực",
    "đội cấn": "Phường Đội Cấn",
    "phường đội cấn": "Phường Đội Cấn",
    "thụy khuê": "Phường Thụy Khuê",
    "phường thụy khuê": "Phường Thụy Khuê",
    "phúc tân": "Phường Phúc Tân",
    "phường phúc tân": "Phường Phúc Tân",
    "xuân hòa": "Phường Xuân Hòa",
    "phường xuân hòa": "Phường Xuân Hòa",
    "bích động": "Thị trấn Bích Động",
    "thị trấn bích động": "Thị trấn Bích Động",
    "đại phúc": "Phường Đại Phúc",
    "phường đại phúc": "Phường Đại Phúc",
    "suối hoa": "Phường Suối Hoa",
    "phường suối hoa": "Phường Suối Hoa",
    "tiền ninh vệ": "Phường Tiền Ninh Vệ",
    "phường tiền ninh vệ": "Phường Tiền Ninh Vệ",
    "đình bảng": "Phường Đình Bảng",
    "phường đình bảng": "Phường Đình Bảng",
    "đông ngàn": "Phường Đông Ngàn",
    "phường đông ngàn": "Phường Đông Ngàn",
    "phượng mao": "Phường Phượng Mao",
    "phường phượng mao": "Phường Phượng Mao",
    "thảo điền": "Phường Thảo Điền",
    "phường thảo điền": "Phường Thảo Điền",
    "phú nhuận": "Phường Phú Nhuận",
    "phường phú nhuận": "Phường Phú Nhuận",
    "cầu kiệu": "Phường Cầu Kiệu",
    "phường cầu kiệu": "Phường Cầu Kiệu",
    "diên hồng": "Phường Diên Hồng",
    "phường diên hồng": "Phường Diên Hồng",
    "an lạc": "Phường An Lạc",
    "phường an lạc": "Phường An Lạc",
    "bình tây": "Phường Bình Tây",
    "phường bình tây": "Phường Bình Tây",
    "tân bình": "Phường Tân Bình",
    "phường tân bình": "Phường Tân Bình",
    "phú lâm": "Phường Phú Lâm",
    "phường phú lâm": "Phường Phú Lâm",
    "tam hiệp": "Phường Tam Hiệp",
    "phường tam hiệp": "Phường Tam Hiệp",
    "trấn biên": "Phường Trấn Biên",
    "phường trấn biên": "Phường Trấn Biên",
    "trảng dài": "Phường Trảng Dài",
    "phường trảng dài": "Phường Trảng Dài",
    "xuân hương - đà lạt": "Phường Xuân Hương - Đà Lạt",
    "phường xuân hương - đà lạt": "Phường Xuân Hương - Đà Lạt",
}


def resolve_province_alias(value: object) -> str:
    """Return canonical province name if an explicit alias or typo matches."""
    cleaned = clean_value(value)
    if not cleaned:
        return ""
    norm = normalise_text(cleaned)
    return PROVINCE_ALIASES.get(norm, cleaned)


def resolve_district_alias(value: object) -> str:
    """Return canonical district name if an explicit alias or typo matches."""
    cleaned = clean_value(value)
    if not cleaned:
        return ""
    norm = normalise_text(cleaned)
    return DISTRICT_ALIASES.get(norm, cleaned)


def resolve_ward_alias(value: object) -> str:
    """Return canonical ward name if an explicit alias or typo matches."""
    cleaned = clean_value(value)
    if not cleaned:
        return ""
    norm = normalise_text(cleaned)
    return WARD_ALIASES.get(norm, cleaned)


def normalize_diff_record(record: dict[str, Any]) -> dict[str, Any]:
    """Apply verified alias lookups to an OSM diff record without losing original fields."""
    normed = dict(record)
    normed["TinhThanh_Cu"] = resolve_province_alias(record.get("TinhThanh_Cu", ""))
    normed["QuanHuyen_Cu"] = resolve_district_alias(record.get("QuanHuyen_Cu", ""))
    normed["PhuongXa_Cu"] = resolve_ward_alias(record.get("PhuongXa_Cu", ""))

    normed["TinhThanh_Moi"] = resolve_province_alias(record.get("TinhThanh_Moi", ""))
    normed["QuanHuyen_Moi"] = resolve_district_alias(record.get("QuanHuyen_Moi", ""))
    normed["PhuongXa_Moi"] = resolve_ward_alias(record.get("PhuongXa_Moi", ""))
    return normed


def normalize_diff_record_with_trace(record: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Normalize a record and list every administrative field changed by an alias.

    The trace is deliberately returned separately so the original OSM tags can
    remain intact in audit exports and every accepted alias stays reviewable.
    """
    normed = normalize_diff_record(record)
    fields = (
        "TinhThanh_Cu",
        "QuanHuyen_Cu",
        "PhuongXa_Cu",
        "TinhThanh_Moi",
        "QuanHuyen_Moi",
        "PhuongXa_Moi",
    )
    changes = [
        f"{field}: {clean_value(record.get(field))} → {clean_value(normed.get(field))}"
        for field in fields
        if clean_value(record.get(field)) != clean_value(normed.get(field))
    ]
    return normed, changes
