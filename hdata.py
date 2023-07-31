import collections
import dataclasses
import logging
from dataclasses import dataclass
from pathlib import Path
import string
from typing import Dict, List, Optional, Tuple

import pcbnew

logger = logging.getLogger("hierpcb")


SchPath = Tuple[str, ...]

FootprintID = str  # Unique id for a footprint across all sub-schematics.


class PCBRoom:
    """Holds the data for a 'room' in the PCB layout, correponding to the layout for a schematic sheet."""

    def __init__(self, path: Path):
        self.path = path
        # Load the room data from the file.
        self.subboard = pcbnew.LoadBoard(str(path))
        assert self.subboard is not None
        logger.info(
            f"Imported {path}, with "
            f"{len(self.subboard.GetFootprints())} footprints, "
            f"{len(self.subboard.GetTracks())} tracks, and "
            f"{len(self.subboard.GetDrawings())} drawings."
        )

    def get_anchor_refs(self) -> Dict[FootprintID, str]:
        """Get the reference prefixes of the footprints that can be used as anchors."""
        rv = {}
        for fp in self.subboard.GetFootprints():
            fid = fp.GetPath().AsString().split("/")[-1]
            rv[fid] = fp.GetReference()

        return rv

    @property
    def is_legal(self) -> bool:
        """Check if the room can be handled by our engine."""
        # For a room to be legal, there must be at least one footprint. That's it.
        return len(self.subboard.GetFootprints()) > 0


class SchSheet:
    """Class to hold information about a schematic sheet."""

    def __init__(self, sheetid: str = "", parent: Optional["SchSheet"] = None) -> None:
        # The sheet identifier, if "", this is the root sheet.
        self.sheetid: str = sheetid
        # The parent sheet. If None, this is the root sheet.
        self.parent: Optional["SchSheet"] = parent

        # The immediate child sheets of this node.
        self.children: Dict[str, "SchSheet"] = {}

        # These are only available if the sheet is referenced by a footprint:
        # The file name of the schematic sheet.
        self.file: Optional[Path] = None
        # The human-readable name of the schematic sheet.
        self.name: Optional[str] = None

        # TODO: Pointer to the PCB layout data.
        self.pcb: Optional[PCBRoom] = False

    def set_metadata(self, file: Path, name: str) -> None:
        self.file = file
        self.name = name

    def has_metadata(self):
        return self.file is not None and self.name is not None

    def get(self, key: SchPath, create=False):
        """Get a sheet by its key."""
        # If the key is empty, we are done.
        if len(key) == 0:
            return self
        # Otherwise the first element of the key is the sheet identifier.
        cons, rest = key[0], key[1:]
        if cons not in self.children:
            if not create:
                raise KeyError(f"Sheet {key} not found in {self.identifier}.")
            self.children[cons] = SchSheet(key, self)
        # Recur on the rest in the child sheet.
        return self.children[cons].get(rest, create)

    @property
    def identifier(self) -> str:
        if self.parent is None:
            return self.sheetid
        return self.parent.identifier / self.sheetid

    @property
    def human_name(self) -> str:
        me = self.name if self.name is not None else self.sheetid[:8]
        if self.parent is None:
            return me
        return self.parent.human_name() + "/" + me

    def __str__(self) -> str:
        me = self.name if self.name is not None else self.sheetid[:8]
        # Head line with the sheet name and whether it has a PCB layout.
        rv = [f"{me}" + (f" (+ PCB {self.pcb.path})" if self.pcb else "")]
        # If there are children, print them.
        for _, child in sorted(self.children.items()):
            c_str = str(child).splitlines()
            # The first line is the child's name, so it should look like a node in the tree.
            rv.append(f"├─ {c_str[0]}")
            for line in c_str[1:]:
                rv.append(f"│  {line}")
        return "\n".join(rv)


class HierarchicalData:
    def __init__(self, board: pcbnew.BOARD):
        self.board = board
        self.root = get_sheet_hierarchy(board)
        pass


def get_sheet_key_from_footprint(fp: pcbnew.FOOTPRINT) -> Optional[SchPath]:
    key = fp.GetPath().AsString().split("/")
    if len(key) <= 1:
        # Skip footprints that are not on a sheet.
        logger.debug(f"Footprint {fp.GetReference()} is not on a sheet, skipping...")
        return None
    assert key[0] == ""
    return tuple(key[1:-1])


def get_sheet_hierarchy(
    board: pcbnew.BOARD,
) -> Tuple[SchSheet, Dict[Path, PCBRoom]]:
    """Infer the sheet hierarchy from footprint data.

    While this should be better handled by examining the schematics, we can't yet do that in KiCad.
    Note that this cannot find sheets that are not referenced by at least one footprint.
    """

    # None means the sheet is known not to have a PCB layout.
    pcb_rooms: Dict[str, Optional[PCBRoom]] = {}
    root_sheets: Optional[SchSheet] = SchSheet("", None)

    for fp in board.GetFootprints():
        key = get_sheet_key_from_footprint(fp)
        # Skip unknown sheets.
        if key is None:
            continue
        # Get the sheet for this footprint, creating it if necessary.
        curr_sheet = root_sheets.get(key, create=True)

        if not curr_sheet.has_metadata():
            try:
                sheet_file = Path(fp.GetProperty("Sheetfile"))
                sheet_name = fp.GetProperty("Sheetname")
            except KeyError:
                logger.debug(f"No Sheetfile for {fp.GetReference()}, skipping.")
                continue

            curr_sheet.set_metadata(sheet_file, sheet_name)

            if sheet_file not in pcb_rooms:
                # If it is not known if the sheet_file does not have an associated PCB layout,
                # then we look for one.
                pcb_file = sheet_file.with_suffix(".kicad_pcb")
                pcb_rooms[sheet_file] = PCBRoom(pcb_file) if pcb_file.exists() else None

            curr_sheet.pcb = pcb_rooms[sheet_file]

    return root_sheets, {k: v for k, v in pcb_rooms.items() if v is not None}
