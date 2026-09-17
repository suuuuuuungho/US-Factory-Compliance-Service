"""Convert ECHO program, subpart, and pollutant CSV rows into records."""

from echo_values import is_missing, parse_date


def _nullable(value: str) -> str | None:
    """Return ``None`` for ECHO's missing-value markers."""

    return None if is_missing(value) else value


def program_row(row: dict[str, str]) -> dict:
    """Convert one PROGRAMS CSV row into an ECHO program record."""

    return {
        "pgm_sys_id": row["PGM_SYS_ID"],
        "program_code": row["PROGRAM_CODE"],
        "description": row["PROGRAM_DESC"],
        "status_code": _nullable(row["AIR_OPERATING_STATUS_CODE"]),
        "status_desc": _nullable(row["AIR_OPERATING_STATUS_DESC"]),
        "begin_date": parse_date(row["BEGIN_DATE"]),
        "updated_date": parse_date(row["UPDATED_DATE"]),
        "raw_dates": {
            "BEGIN_DATE": row["BEGIN_DATE"],
            "UPDATED_DATE": row["UPDATED_DATE"],
        },
    }


def subpart_row(row: dict[str, str], code_map: dict[str, dict]) -> dict:
    """Convert one PROGRAM_SUBPARTS CSV row using its official code mapping."""

    subpart_code = row["AIR_PROGRAM_SUBPART_CODE"]
    mapping = code_map.get(subpart_code)
    cfr_title = cfr_part = cfr_subpart = None
    mapping_status = "unresolved"
    if mapping is not None:
        mapping_status = mapping["review_status"]
        if mapping_status == "ok":
            cfr_title = int(mapping["cfr_title"])
            cfr_part = mapping["cfr_part"]
            cfr_subpart = mapping["cfr_subpart"]
            mapping_status = "mapped"

    return {
        "pgm_sys_id": row["PGM_SYS_ID"],
        "program_code": row["PROGRAM_CODE"],
        "subpart_code": subpart_code,
        "subpart_desc": row["AIR_PROGRAM_SUBPART_DESC"],
        "cfr_title": cfr_title,
        "cfr_part": cfr_part,
        "cfr_subpart": cfr_subpart,
        "mapping_status": mapping_status,
    }


def pollutant_row(row: dict[str, str], source_row_no: int) -> dict:
    """Convert one POLLUTANTS CSV row into an ECHO pollutant record."""

    pollutant_code = _nullable(row["POLLUTANT_CODE"])
    return {
        "pgm_sys_id": row["PGM_SYS_ID"],
        "pollutant_key": pollutant_code or f"row:{source_row_no}",
        "pollutant_code": pollutant_code,
        "description": row["POLLUTANT_DESC"],
        "srs_id": _nullable(row["SRS_ID"]),
        "cas_number": _nullable(row["CHEMICAL_ABSTRACT_SERVICE_NMBR"]),
        "class_code": _nullable(row["AIR_POLLUTANT_CLASS_CODE"]),
        "class_desc": _nullable(row["AIR_POLLUTANT_CLASS_DESC"]),
        "source_locator": f"ICIS-AIR_POLLUTANTS.csv:{source_row_no}",
        "review_status": "ok" if pollutant_code is not None else "unresolved",
    }
