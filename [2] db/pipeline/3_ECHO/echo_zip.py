"""Validate ECHO ZIP downloads and describe their members without extracting them."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import io
from pathlib import Path, PurePosixPath
from typing import Sequence
import zipfile


ICIS_AIR_MEMBERS = (
    "ICIS-AIR_FACILITIES.csv",
    "ICIS-AIR_PROGRAMS.csv",
    "ICIS-AIR_PROGRAM_SUBPARTS.csv",
    "ICIS-AIR_POLLUTANTS.csv",
    "ICIS-AIR_FCES_PCES.csv",
    "ICIS-AIR_STACK_TESTS.csv",
    "ICIS-AIR_TITLEV_CERTS.csv",
    "ICIS-AIR_FORMAL_ACTIONS.csv",
    "ICIS-AIR_INFORMAL_ACTIONS.csv",
    "ICIS-AIR_VIOLATION_HISTORY.csv",
)
PIPELINE_MEMBERS = ("PIPELINE_CAA_00_COMPLETE.csv",)


class ZipCheckError(ValueError):
    """A downloaded ECHO ZIP is invalid or does not have its required members."""


@dataclass(frozen=True)
class MemberSpec:
    name: str
    byte_size: int
    header: list[str] | None
    row_count: int | None


def inspect_zip(path: Path, *, required: Sequence[str]) -> list[MemberSpec]:
    """Check *path* and return metadata for every non-directory ZIP member."""

    if not zipfile.is_zipfile(path):
        raise ZipCheckError(f"not a ZIP file: {path}")

    try:
        with zipfile.ZipFile(path) as zf:
            infos = [info for info in zf.infolist() if not info.is_dir()]
            names = [info.filename for info in infos]
            for name in names:
                parts = PurePosixPath(name).parts
                if ".." in parts or name.startswith(("/", "\\")) or ":" in name:
                    raise ZipCheckError(f"unsafe member path: {name}")

            missing = [name for name in required if name not in names]
            if missing:
                raise ZipCheckError(f"missing required members: {', '.join(missing)}")

            bad_member = zf.testzip()
            if bad_member is not None:
                raise ZipCheckError(f"CRC mismatch in {bad_member}")

            specs = []
            for info in infos:
                header: list[str] | None = None
                row_count: int | None = None
                if info.filename.lower().endswith(".csv"):
                    with zf.open(info) as raw, io.TextIOWrapper(
                        raw, encoding="utf-8-sig", newline=""
                    ) as text:
                        reader = csv.reader(text)
                        header = next(reader, None) or []
                        row_count = sum(1 for _ in reader)
                specs.append(MemberSpec(info.filename, info.file_size, header, row_count))
            return specs
    except zipfile.BadZipFile as error:
        raise ZipCheckError(f"CRC mismatch in {path}") from error
