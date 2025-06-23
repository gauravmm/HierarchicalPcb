import logging
import math
from itertools import zip_longest
from typing import Callable, Dict, List, Optional, Tuple

import pcbnew

from .hdata import HierarchicalData, PCBRoom, SchSheet

logger = logging.getLogger("hierpcb")


class ErrorLevel:
    INFO = 0
    WARNING = 1
    ERROR = 2


class ReportedError:
    def __init__(
        self,
        title: str,
        message: Optional[str] = None,
        level: ErrorLevel = ErrorLevel.ERROR,
        footprint: pcbnew.FOOTPRINT = None,
        sheet: SchSheet = None,
        pcb: PCBRoom = None,
    ):
        self.title = title
        self.message = message
        self.level = level
        self.footprint = footprint
        self.sheet = sheet
        self.pcb = pcb

        logger.debug(str(self))

    def __str__(self):
        msg = [f"ERR.{self.level}\t{self.title}"]
        if self.message:
            msg += [f" Message: {self.message}"]
        if self.footprint:
            msg += [f" Footprint: {self.footprint.GetReference()}"]
        if self.sheet:
            msg += [f" Sheet: {self.sheet.identifier}"]
        if self.pcb:
            msg += [f" SubPCB: {self.pcb.path}"]

        return "\n".join(msg)


class PositionTransform:
    def __init__(self, template: pcbnew.FOOTPRINT, mutate: pcbnew.FOOTPRINT) -> None:
        # These are stored such that adding these to the position and rotation of the `template`
        # will yield the position and rotation of the `mutate`.
        self.anchor_template = template
        self.anchor_mutate = mutate

    def translate(self, pos_template: pcbnew.VECTOR2I) -> pcbnew.VECTOR2I:
        # Find the position of fp_template relative to the anchor_template:
        delta_x: int = pos_template.x - self.anchor_template.GetPosition().x
        delta_y: int = pos_template.y - self.anchor_template.GetPosition().y
        rotation = math.radians(
            self.anchor_mutate.GetOrientationDegrees()
            - self.anchor_template.GetOrientationDegrees()
        )

        # With this information, we can compute the net position after any rotation:
        new_x = (
            delta_y * math.sin(rotation)
            + delta_x * math.cos(rotation)
            + self.anchor_mutate.GetPosition().x
        )
        new_y = (
            delta_y * math.cos(rotation)
            - delta_x * math.sin(rotation)
            + self.anchor_mutate.GetPosition().y
        )
        return pcbnew.VECTOR2I(int(new_x), int(new_y))

    def orient(self, rot_template: float):
        return (
            rot_template
            - self.anchor_template.GetOrientation()
            + self.anchor_mutate.GetOrientation()
        )


GroupMoverType = Callable[[pcbnew.BOARD_ITEM], bool]


class GroupManager:
    def __init__(self, board: pcbnew.BOARD) -> None:
        self.board: pcbnew.board = board
        self.groups: Dict[str, pcbnew.PCB_GROUP] = {
            g.GetName(): g for g in board.Groups()
        }

    def create_or_get(self, group_name: str) -> pcbnew.PCB_GROUP:
        """Get a group by name, creating it if it doesn't exist."""
        group = self.groups.get(group_name)
        if group is None:
            group = pcbnew.PCB_GROUP(None)
            group.SetName(group_name)
            self.board.Add(group)
            self.groups[group_name] = group
        return group

    def move(self, item: pcbnew.BOARD_ITEM, group: Optional[pcbnew.PCB_GROUP]) -> bool:
        """Force an item to be in a group., returning True if the item was moved."""
        if group is None:
            return False
        moved = False

        # First, check if the footprint is already in the group:
        parent_group = item.GetParentGroup()
        # If the footprint is not already in the group, remove it from the current group:
        if parent_group and parent_group.GetName() != group.GetName():
            moved = True
            parent_group.RemoveItem(item)
            parent_group = None
        # If the footprint is not in any group, or was in the wrong group, add it to the right one:
        if parent_group is None:
            group.AddItem(item)

        return moved

    def mover(self, group: pcbnew.PCB_GROUP) -> GroupMoverType:
        """Return a function that moves an item to the given group."""
        return lambda item: self.move(item, group)


def enforce_position(hd: HierarchicalData, targetBoard: pcbnew.BOARD):
    """Enforce the positions of objects in PCB template on PCB mutate."""
    # Prepare a lookup table for footprints in the board:
    # Since board.FindFootprintByPath() operates on a custom type that we can't easily
    # construct, we prepare a table for efficient string lookups instead.
    fp_lookup = {fp.GetPath().AsString(): fp for fp in targetBoard.GetFootprints()}

    errors: List[ReportedError] = []
    groupman: GroupManager = GroupManager(targetBoard)

    for sheet in hd.root_sheet.tree_iter():
        if sheet.pcb and sheet.checked:
            # Check if the sub-PCB is legal:
            if not sheet.pcb.is_legal:
                errors.append(ReportedError("sub-PCB cannot be placed", pcb=sheet.pcb))
                continue

            # Find the anchor footprint on the subPCB:
            anchor_subpcb = sheet.pcb.selected_anchor
            if not anchor_subpcb:
                errors.append(
                    ReportedError(
                        "sub-PCB has no anchor selected",
                        pcb=sheet.pcb,
                        level=ErrorLevel.ERROR,
                    )
                )
                continue

            # Find the anchor footprint on the board:
            anchor_path = sheet.identifier + anchor_subpcb.GetPath().AsString()
            anchor_target = fp_lookup.get(anchor_path)

            if not anchor_target:
                errors.append(
                    ReportedError(
                        "anchor not found on target",
                        message=f"Expected path {anchor_path}",
                        pcb=sheet.pcb,
                        level=ErrorLevel.ERROR,
                    )
                )
                continue

            # We need to force all the footprints to be in the same group. To do that,
            # we automatically create a group for the anchor footprint if it doesn't exist and
            # move all the footprints into it.
            group_name = f"subpcb_{sheet.human_path}"
            group = groupman.create_or_get(group_name)

            # Clear Volatile items first
            clear_volatile_items(targetBoard, group)

            if groupman.move(anchor_target, group):
                errors.append(
                    ReportedError(
                        "anchor footprint is in the wrong group",
                        message=f"Expected group {group_name}",
                        pcb=sheet.pcb,
                        level=ErrorLevel.ERROR,
                    )
                )

            # Compute the transform for later use:
            transform = PositionTransform(anchor_subpcb, anchor_target)

            # First, move the footprints:
            footprintNetMapping, err_footprints = enforce_position_footprints(
                sheet, transform, fp_lookup, groupman.mover(group)
            )
            errors.extend(err_footprints)

            # Recreate traces:
            err_traces = copy_traces(targetBoard, sheet, transform, groupman.mover(group), footprintNetMapping)
            errors.extend(err_traces)

            # Recreate Drawings
            err_drawings = copy_drawings(targetBoard,sheet,transform, groupman.mover(group))
            errors.extend(err_drawings)

            # Recreate Zones Currently Using Work around
            # zone.SetPosition() doesn't change position
            # for some reason?
            err_zones = copy_zones(targetBoard,sheet,transform, groupman.mover(group), footprintNetMapping)
            errors.extend(err_zones)

    #Fixes issues with traces lingering after being deleted
    pcbnew.Refresh()


def clear_volatile_items(targetBoard: pcbnew.BOARD, group: pcbnew.PCB_GROUP):
    """Remove all zones in a group."""
    itemTypesToRemove = (
        # Traces
        pcbnew.PCB_TRACK, pcbnew.ZONE,
        # Drawings
        pcbnew.PCB_SHAPE, pcbnew.PCB_TEXT,
        # Zones
        pcbnew.ZONE
    )

    for item in group.GetItems():

        # Gets all drawings in a group
        if isinstance(item.Cast(), itemTypesToRemove):
            # Remove every drawing
            targetBoard.RemoveNative(item)


def copy_traces(
    targetBoard: pcbnew.BOARD,
    sheet: SchSheet,
    transform: PositionTransform,
    mover: GroupMoverType,
    footprintNetMapping: Dict[int, int],
):
    # Instead of figuring out which nets are connected to the sub-PCB, we just copy all the raw traces
    # and let KiCad figure it out. It seems to work so far.

    errors = []
    for sourceTrack in sheet.pcb.subboard.Tracks():
        # Copy track to trk:
        # logger.info(f"{track} {type(track)} {track.GetStart()} -> {track.GetEnd()}")
        
        newTrack = sourceTrack.Duplicate()

        # Sets the track end point
        # the start is handled by item.SetPosition
        targetBoard.Add(newTrack)

        sourceNetCode = sourceTrack.GetNetCode()
        newNetCode = footprintNetMapping.get(sourceNetCode, 0)
        newTrack.SetNet(targetBoard.FindNet(newNetCode))

        newTrack.SetStart(transform.translate(sourceTrack.GetStart()))
        newTrack.SetEnd  (transform.translate(sourceTrack.GetEnd()  ))

        if type(newTrack) == pcbnew.PCB_VIA:
            newTrack.SetIsFree(False)

        mover(newTrack)

    return errors


def copy_drawings(
    targetBoard: pcbnew.BOARD,
    sheet: SchSheet,
    transform: PositionTransform,
    mover: GroupMoverType,
):

    errors = []
    for sourceDrawing in sheet.pcb.subboard.GetDrawings(): 
        
        newDrawing = sourceDrawing.Duplicate()

        targetBoard.Add(newDrawing)

        # Set New Position
        newDrawing.SetPosition(transform.translate(sourceDrawing.GetPosition()))

        # Drawings dont have .SetOrientation()
        # instead do a relative rotation
        newDrawing.Rotate(newDrawing.GetPosition(), transform.orient(pcbnew.ANGLE_0))

        mover(newDrawing)

    return errors


def copy_zones(
    targetBoard: pcbnew.BOARD,
    sheet: SchSheet,
    transform: PositionTransform,
    mover: GroupMoverType,
    footprintNetMapping: Dict[int, int],
):

    errors = []
    for sourceZone in sheet.pcb.subboard.Zones():
        # if isinstance(drawing, pcbnew.PCB_SHAPE):
        #     newShape = pcbnew.PCB_SHAPE()
        # elif isinstance(drawing, pcbnew.PCB_TEXT):
        #     newShape = pcbnew.PCB_TEXT()   
        
        newZone = sourceZone.Duplicate()

        sourceNetCode = sourceZone.GetNetCode()
        newNetCode = footprintNetMapping.get(sourceNetCode, 0)
        newZone.SetNet(targetBoard.FindNet(newNetCode))

        targetBoard.Add(newZone)

        # Set New Position
        # newZone.SetPosition(transform.translate(zone.GetPosition()))
        # Temporary Workaround:
        
        # Move zone to 0,0 by moving relative
        newZone.Move(-newZone.GetPosition())
        # Move zone to correct location
        newZone.Move(transform.translate(sourceZone.GetPosition()))

        # Drawings dont have .SetOrientation()
        # instead do a relative rotation
        newZone.Rotate(newZone.GetPosition(), transform.orient(pcbnew.ANGLE_0))

        mover(newZone)

    return errors


def copy_footprint_fields(
    sourceFootprint: pcbnew.FOOTPRINT,
    targetFootprint: pcbnew.FOOTPRINT, 
    transform: PositionTransform,
):
    # NOTE: Non center aligned Fields position changes with rotation.
    #       This is not a bug. The replicated pcbs are behaving the 
    #       exact same as the original would when rotated.

    if len(sourceFootprint.GetFields()) != len(targetFootprint.GetFields())
        logger.info("Number of footprint fields dont match")
        return

    # Do any other field values need preserved?
    originalReference = targetFootprint.GetReference()

    # Remove Existing footprint fields
    for targetField in targetFootprint.GetFields():
        sourceField = sourceFootprint.GetFieldByName(
            targetField.GetName()
        )
        if not sourceField:
            logger.info("Field not found by name")
            continue

        targetField.SetPosition(transform.translate(sourceField.GetPosition()))
        targetField.SetTextAngle(
            transform.orient(sourceField.GetTextAngle())
        )

    targetFootprint.SetReference(originalReference)


def copy_footprint_data(
    sourceFootprint: pcbnew.FOOTPRINT,
    targetFootprint: pcbnew.FOOTPRINT, 
    transform: PositionTransform,
):
    if sourceFootprint.IsFlipped() != targetFootprint.IsFlipped():
        targetFootprint.Flip(targetFootprint.GetPosition(), False)

    # The list of properties is from the ReplicateLayout plugin. Thanks @MitjaNemec!
    targetFootprint.SetLocalClearance(sourceFootprint.GetLocalClearance())
    targetFootprint.SetLocalSolderMaskMargin(sourceFootprint.GetLocalSolderMaskMargin())
    targetFootprint.SetLocalSolderPasteMargin(sourceFootprint.GetLocalSolderPasteMargin())
    targetFootprint.SetLocalSolderPasteMarginRatio(
        sourceFootprint.GetLocalSolderPasteMarginRatio()
    )
    targetFootprint.SetLocalZoneConnection(sourceFootprint.GetLocalZoneConnection())

    # Move the footprint:
    targetFootprint.SetPosition(transform.translate(sourceFootprint.GetPosition()))
    targetFootprint.SetOrientation(transform.orient(sourceFootprint.GetOrientation()))


def enforce_position_footprints(
    sheet: SchSheet,
    transform: PositionTransform,
    fp_lookup: Dict[str, pcbnew.FOOTPRINT],
    groupmv: GroupMoverType,
):
    errors = []

    # The keys are the sub-pcb net codes
    # The values are the new net codes
    footprintNetMapping = {}

    # For each footprint in the sub-PCB, find the corresponding footprint on the board:
    for sourceFootprint in sheet.pcb.subboard.GetFootprints():
        # Find the corresponding footprint on the board:
        fp_path = sheet.identifier + sourceFootprint.GetPath().AsString()
        targetFootprint = fp_lookup.get(fp_path)

        if not targetFootprint:
            errors.append(
                ReportedError(
                    "footprint not found, skipping",
                    message=f"Corresponding to {sourceFootprint.GetReference()} for sheet {sheet.human_name}",
                    footprint=sourceFootprint,
                    pcb=sheet.pcb,
                    level=ErrorLevel.WARNING,
                )
            )
            continue

        # TODO: Ignore footprints outside the lower-right quadrant.

        # Copy the properties and move the template to the target:
        copy_footprint_data(sourceFootprint, targetFootprint, transform)
        
        copy_footprint_fields(sourceFootprint, targetFootprint, transform)

        # Assumes pads are ordered by the pad number
        for sourcePadNum, sourcePad in enumerate(sourceFootprint.Pads()):
            targetPad = targetFootprint.Pads()[sourcePadNum]

            sourceCode = sourcePad.GetNetCode()
            targetCode = targetPad.GetNetCode()
            
            footprintNetMapping[sourceCode] = targetCode

        # Move the footprint into the group if one is provided:
        if groupmv(targetFootprint):
            errors.append(
                ReportedError(
                    f"footprint {targetFootprint} is in the wrong group",
                    pcb=sheet.pcb,
                    level=ErrorLevel.ERROR,
                )
            )

    return (footprintNetMapping, errors)
