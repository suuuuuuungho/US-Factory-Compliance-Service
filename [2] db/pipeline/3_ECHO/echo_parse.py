"""Stream an ECHO release into parsed JSONL tables and a quality report."""

from contextlib import ExitStack
import csv
from datetime import date
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import zipfile

from echo_activities import activity_rows
from echo_actions import action_rows
from echo_facility import facility_rows
from echo_pipeline import _FLAG_COLUMNS, pipeline_row
from echo_programs import pollutant_row, program_row, subpart_row
from echo_rows import iter_rows
from echo_violations import violation_rows
from echo_zip import ICIS_AIR_MEMBERS, PIPELINE_MEMBERS


class ParseError(ValueError):
    """An ECHO member does not contain its required columns."""


TABLES = (
    "echo_source_row", "echo_facility", "echo_facility_identifier", "echo_industry",
    "echo_program", "echo_program_subpart", "echo_pollutant", "echo_activity",
    "echo_activity_facility", "echo_violation", "echo_violation_facility",
    "echo_penalty", "echo_pipeline_link",
)
REQUIRED = {
    "ICIS-AIR_FACILITIES.csv": ("PGM_SYS_ID",),
    "ICIS-AIR_PROGRAMS.csv": ("PGM_SYS_ID", "PROGRAM_CODE"),
    "ICIS-AIR_PROGRAM_SUBPARTS.csv": ("PGM_SYS_ID", "PROGRAM_CODE", "AIR_PROGRAM_SUBPART_CODE"),
    "ICIS-AIR_POLLUTANTS.csv": ("PGM_SYS_ID", "POLLUTANT_CODE"),
    "ICIS-AIR_FCES_PCES.csv": ("PGM_SYS_ID", "ACTIVITY_ID", "ACTUAL_END_DATE"),
    "ICIS-AIR_STACK_TESTS.csv": ("PGM_SYS_ID", "ACTIVITY_ID", "ACTUAL_END_DATE"),
    "ICIS-AIR_TITLEV_CERTS.csv": ("PGM_SYS_ID", "ACTIVITY_ID", "ACTUAL_END_DATE"),
    "ICIS-AIR_FORMAL_ACTIONS.csv": ("PGM_SYS_ID", "ACTIVITY_ID", "SETTLEMENT_ENTERED_DATE", "PENALTY_AMOUNT"),
    "ICIS-AIR_INFORMAL_ACTIONS.csv": ("PGM_SYS_ID", "ACTIVITY_ID", "ACHIEVED_DATE"),
    "ICIS-AIR_VIOLATION_HISTORY.csv": ("PGM_SYS_ID", "ACTIVITY_ID"),
    "PIPELINE_CAA_00_COMPLETE.csv": ("SOURCE_ID", "EVAL_ACTIVITY_ID", "VIOL_ACTIVITY_ID", "EA_ACTIVITY_ID", "EA_FEA_ACTIVITY_ID", *_FLAG_COLUMNS),
}
KEYS = {
    "echo_facility": ("pgm_sys_id",), "echo_facility_identifier": ("program_system", "pgm_sys_id", "registry_id"),
    "echo_industry": ("pgm_sys_id", "code_system", "code"), "echo_program": ("pgm_sys_id", "program_code"),
    "echo_program_subpart": ("pgm_sys_id", "program_code", "subpart_code"), "echo_pollutant": ("pgm_sys_id", "pollutant_key"),
    "echo_activity": ("activity_kind", "activity_id"), "echo_activity_facility": ("activity_kind", "activity_id", "pgm_sys_id"),
    "echo_violation": ("violation_id",), "echo_violation_facility": ("violation_id", "pgm_sys_id"),
    "echo_pipeline_link": ("link_key",),
}
CONFLICTS = {"echo_facility", "echo_program", "echo_program_subpart", "echo_pollutant", "echo_activity", "echo_violation"}
ORPHANS = ("echo_industry.pgm_sys_id", "echo_program.pgm_sys_id", "echo_program_subpart.program", "echo_pollutant.pgm_sys_id", "echo_activity_facility.pgm_sys_id", "echo_activity_facility.activity", "echo_violation_facility.pgm_sys_id", "echo_violation_facility.violation", "echo_penalty.activity", "echo_pipeline_link.resolved")


def _plain(value):
    if isinstance(value, (date, Decimal)):
        return value.isoformat() if isinstance(value, date) else str(value)
    raise TypeError


def _digest(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, default=_plain).encode()).hexdigest()


def _headers(zip_path: Path, member: str) -> list[str]:
    with zipfile.ZipFile(zip_path) as archive, archive.open(member) as raw:
        return next(csv.reader((line.decode("utf-8-sig") for line in raw)))


def _code_map(path: Path) -> dict[str, dict]:
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        key = item["raw_subpart_code"]
        if key in result:
            result[key] = {**result[key], "review_status": "conflict"}
        else:
            result[key] = item
    return result


def parse_release(root: Path, as_of: date, code_map_version: str) -> dict:
    """Parse a raw ECHO release without retaining CSV rows in memory."""
    raw_dir = root / "raw" / as_of.isoformat()
    manifest = json.loads((raw_dir / "manifest.json").read_text(encoding="utf-8"))
    objects = {item["name"]: item for item in manifest}
    icis = root / objects["ICIS-AIR_downloads.zip"]["path"]
    pipeline = root / objects["pipeline_caa_downloads.zip"]["path"]
    member_sources = {member: (icis, objects["ICIS-AIR_downloads.zip"]["sha256"]) for member in ICIS_AIR_MEMBERS}
    member_sources[PIPELINE_MEMBERS[0]] = (pipeline, objects["pipeline_caa_downloads.zip"]["sha256"])
    for member in (*ICIS_AIR_MEMBERS, *PIPELINE_MEMBERS):
        header = _headers(member_sources[member][0], member)
        missing = [column for column in REQUIRED[member] if column not in header]
        if missing:
            raise ParseError(f"{member}: missing required columns: {', '.join(missing)}")

    report = {
        "as_of": as_of.isoformat(), "code_map_version": code_map_version,
        "files": {member: {"read": 0, "ok": 0, "held": 0} for member in (*ICIS_AIR_MEMBERS, *PIPELINE_MEMBERS)},
        "identifiers": {}, "orphans": {key: 0 for key in ORPHANS},
        "duplicates": {table: 0 for table in KEYS},
        "conflicts": {table: 0 for table in CONFLICTS},
        "conflict_examples": {table: [] for table in CONFLICTS},
        "penalties": {"rows": 0, "formal_rows_ok": 0},
        "subpart_mapping": {"mapped": 0, "unresolved": 0, "conflict": 0},
        "pipeline": {"resolved": 0, "unresolved": 0, "none": 0, "synthetic_violation": 0},
    }
    output = root / "parsed" / as_of.isoformat()
    output.mkdir(parents=True)
    seen = {table: {} for table in KEYS}
    facilities, programs, activities, violations = set(), set(), set(), set()
    code_map = _code_map(root / "code_map" / code_map_version / "echo_code_map.jsonl")

    with ExitStack() as stack:
        writers = {table: stack.enter_context((output / f"{table}.jsonl").open("w", encoding="utf-8")) for table in TABLES}

        def write(table, row, member, number):
            if table in KEYS:
                key = tuple(row[field] for field in KEYS[table])
                digest = _digest(row)
                if key in seen[table]:
                    if seen[table][key] == digest or table not in CONFLICTS:
                        report["duplicates"][table] += 1
                    else:
                        report["conflicts"][table] += 1
                        examples = report["conflict_examples"][table]
                        if len(examples) < 20:
                            examples.append({"key": list(key), "source_file": member, "source_row_no": number})
                    return False
                seen[table][key] = digest
            writers[table].write(json.dumps(row, ensure_ascii=False, default=_plain) + "\n")
            return True

        for member in (*ICIS_AIR_MEMBERS, *PIPELINE_MEMBERS):
            zip_path, object_sha = member_sources[member]
            identifier_columns = [column for column in ("PGM_SYS_ID", "ACTIVITY_ID", "SOURCE_ID") if column in REQUIRED[member] or column in _headers(zip_path, member)]
            values = {column: set() for column in identifier_columns}
            stats = {column: {"missing": 0, "duplicate": 0} for column in identifier_columns}
            for number, row in iter_rows(zip_path, member):
                report["files"][member]["read"] += 1
                for column in identifier_columns:
                    value = row[column]
                    if value == "": stats[column]["missing"] += 1
                    elif value in values[column]: stats[column]["duplicate"] += 1
                    else: values[column].add(value)
                try:
                    if member == "ICIS-AIR_FACILITIES.csv":
                        facility, industries = facility_rows(row); records = [("echo_facility", facility)] + [("echo_industry", item) for item in industries]
                        if facility["registry_id"] is not None: records.append(("echo_facility_identifier", {"program_system": "ICIS-AIR", "pgm_sys_id": facility["pgm_sys_id"], "registry_id": facility["registry_id"], "mapping_source": member, "review_status": "source_stated"}))
                    elif member == "ICIS-AIR_PROGRAMS.csv": records = [("echo_program", program_row(row))]
                    elif member == "ICIS-AIR_PROGRAM_SUBPARTS.csv": records = [("echo_program_subpart", subpart_row(row, code_map))]
                    elif member == "ICIS-AIR_POLLUTANTS.csv": records = [("echo_pollutant", pollutant_row(row, number))]
                    elif member in ("ICIS-AIR_FCES_PCES.csv", "ICIS-AIR_STACK_TESTS.csv", "ICIS-AIR_TITLEV_CERTS.csv"):
                        kind = {"ICIS-AIR_FCES_PCES.csv": "inspection", "ICIS-AIR_STACK_TESTS.csv": "stack_test", "ICIS-AIR_TITLEV_CERTS.csv": "titlev"}[member]; activity, link = activity_rows(kind, row); records = [("echo_activity", activity), ("echo_activity_facility", link)]
                    elif member in ("ICIS-AIR_FORMAL_ACTIONS.csv", "ICIS-AIR_INFORMAL_ACTIONS.csv"):
                        kind = "formal" if "FORMAL" in member and "INFORMAL" not in member else "informal"; activity, link, penalty = action_rows(kind, row, number); records = [("echo_activity", activity), ("echo_activity_facility", link)] + ([] if penalty is None else [("echo_penalty", penalty)])
                    elif member == "ICIS-AIR_VIOLATION_HISTORY.csv":
                        violation, link = violation_rows(row); records = [("echo_violation", violation), ("echo_violation_facility", link)]
                    else: records = [("echo_pipeline_link", pipeline_row(row, number, activities | violations))]
                    for table, item in records:
                        added = write(table, item, member, number)
                        if added and table == "echo_facility": facilities.add(item["pgm_sys_id"])
                        if added and table == "echo_program": programs.add((item["pgm_sys_id"], item["program_code"]))
                        if added and table == "echo_activity": activities.add((item["activity_kind"], item["activity_id"]))
                        if added and table == "echo_violation": violations.add(("violation", item["violation_id"]))
                        if added and table == "echo_penalty": report["penalties"]["rows"] += 1
                        if table == "echo_program_subpart" and added: report["subpart_mapping"][item["mapping_status"]] += 1
                        if table == "echo_pipeline_link" and added:
                            report["pipeline"][item["resolution_status"]] += 1; report["pipeline"]["synthetic_violation"] += item["synthetic_violation"]
                    report["files"][member]["ok"] += 1
                    if member == "ICIS-AIR_FORMAL_ACTIONS.csv": report["penalties"]["formal_rows_ok"] += 1
                except (KeyError, ValueError) as error:
                    report["files"][member]["held"] += 1
                    records = []
                    write("echo_source_row", {"source_file": member, "source_row_no": number, "raw_payload": row, "row_hash": hashlib.sha256("\x1f".join(row.values()).encode()).hexdigest(), "parse_status": "held", "error": f"{type(error).__name__}: {error}", "source_object_sha256": object_sha}, member, number)
                    continue
                write("echo_source_row", {"source_file": member, "source_row_no": number, "raw_payload": row, "row_hash": hashlib.sha256("\x1f".join(row.values()).encode()).hexdigest(), "parse_status": "ok", "error": None, "source_object_sha256": object_sha}, member, number)
            read = report["files"][member]["read"]
            report["identifiers"][member] = {column: {"missing": data["missing"], "missing_rate": round(data["missing"] / read, 4), "duplicate": data["duplicate"], "duplicate_rate": round(data["duplicate"] / read, 4)} for column, data in stats.items()}
    # Relationship checks are based on retained rows only.
    for table, entries in seen.items():
        for key in entries:
            if table == "echo_industry" and key[0] not in facilities: report["orphans"]["echo_industry.pgm_sys_id"] += 1
            if table == "echo_program" and key[0] not in facilities: report["orphans"]["echo_program.pgm_sys_id"] += 1
            if table == "echo_program_subpart" and key[:2] not in programs: report["orphans"]["echo_program_subpart.program"] += 1
            if table == "echo_pollutant" and key[0] not in facilities: report["orphans"]["echo_pollutant.pgm_sys_id"] += 1
            if table == "echo_activity_facility":
                if key[2] not in facilities: report["orphans"]["echo_activity_facility.pgm_sys_id"] += 1
                if key[:2] not in activities: report["orphans"]["echo_activity_facility.activity"] += 1
            if table == "echo_violation_facility":
                if key[1] not in facilities: report["orphans"]["echo_violation_facility.pgm_sys_id"] += 1
                if ("violation", key[0]) not in violations: report["orphans"]["echo_violation_facility.violation"] += 1
            if table == "echo_penalty" and ("formal", None) in activities: pass
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    return report
