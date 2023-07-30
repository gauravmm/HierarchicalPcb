from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pcbnew

import logging

logger = logging.getLogger("hierpcb.hierarchical")


@dataclass
class SchSheet:
    """Class to hold information about a schematic sheet."""

    key: str  # The full sheet identifier.
    file: Path  # The file name of the schematic sheet.
    name: str  # The human-readable name of the schematic sheet.
    has_pcb: bool = False
    parent: Optional["SchSheet"] = None  # The sheet identifier for the parent.


class HierarchicalData:
    def __init__(self, board: pcbnew.BOARD):
        self.board = board
        pass


def get_sheet_hierarchy(
    board: pcbnew.BOARD,
) -> List[SchSheet]:
    """Infer the sheet hierarchy from footprint data.

    While this should be better handled by examining the schematics, we can't yet do that in KiCad.
    Note that this cannot find sheets that are not referenced by at least one footprint.
    """

    sheets: Dict[str, SchSheet] = {}

    for fp in board.GetFootprints():
        key = fp.GetPath()

        logger.info(f"{fp.GetReference()} -- {key}")

        # Skip sheets that have already been processed.
        if key in sheets:
            continue
        # Skip footprints that are not on a sheet.
        try:
            sheet_file = fp.GetProperty("Sheetfile")
            sheet_name = fp.GetProperty("Sheetname")
        except KeyError:
            logger.debug(f"Skipping {fp.GetReference()} -- no Sheetfile.")
            continue``

        # Footprint is on a sheet.
        sheets[key] = SchSheet(
            key=key,
            file=sheet_file,
            name=sheet_name,
            has_pcb=False,
            parent=None,
        )
