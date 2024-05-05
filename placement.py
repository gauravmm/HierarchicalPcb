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

    def footprint(
        self, fp_template: pcbnew.FOOTPRINT, fp_mutate: pcbnew.FOOTPRINT
    ) -> None:
        """Transform fp_mutate so it is in the same position as fp_template, but relative to the mutate_anchor."""
        if fp_template.IsFlipped() != fp_mutate.IsFlipped():
            fp_mutate.Flip(fp_mutate.GetPosition(), False)

        # The list of properties is from the ReplicateLayout plugin. Thanks @MitjaNemec!
        fp_mutate.SetLocalClearance(fp_template.GetLocalClearance())
        fp_mutate.SetLocalSolderMaskMargin(fp_template.GetLocalSolderMaskMargin())
        fp_mutate.SetLocalSolderPasteMargin(fp_template.GetLocalSolderPasteMargin())
        fp_mutate.SetLocalSolderPasteMarginRatio(
            fp_template.GetLocalSolderPasteMarginRatio()
        )
        fp_mutate.SetZoneConnection(fp_template.GetZoneConnection())

        # Move the footprint:
        # Find the position of fp_template relative to the anchor_template:

        fp_mutate.SetPosition(self.translate(fp_template.GetPosition()))
        fp_mutate.SetOrientation(self.orient(fp_template.GetOrientation()))

    def footprint_text(
        self,
        src: Optional[pcbnew.PCB_FIELD],
        dst: Optional[pcbnew.PCB_FIELD],
        dst_fp: Optional[pcbnew.FOOTPRINT] = None,
    ):
        """Move dst to the same position as src, but relative to the anchor_mutate."""

        if type(src) == type(dst) == pcbnew.PCB_FIELD:
            dst.SetLayer(src.GetLayer())
            dst.SetTextThickness(src.GetTextThickness())
            dst.SetTextWidth(src.GetTextWidth())
            dst.SetTextHeight(src.GetTextHeight())
            dst.SetItalic(src.IsItalic())
            dst.SetBold(src.IsBold())
            dst.SetMultilineAllowed(src.IsMultilineAllowed())
            dst.SetHorizJustify(src.GetHorizJustify())
            dst.SetVertJustify(src.GetVertJustify())
            dst.SetKeepUpright(src.IsKeepUpright())
            dst.SetVisible(src.IsVisible())

            dst.SetMirrored(src.IsMirrored())

            # Move the text:
            dst.SetPosition(self.translate(src.GetPosition()))
            # The rotation stacks with the rotation of the footprint, so we don't need to
            # set the rotation here. TODO: Check this with a bunch of rotations.
            # The rotation still should be set so user modification doesn't result in messed up clones
            dst.SetTextAngle(self.orient(src.GetTextAngle()))

        elif type(src) == pcbnew.PCB_FIELD:
            # We have a source but no destination. We should eventually add support for
            # creating a new text object, but not now.
            # TODO: Support creating text objects.
            pass

        elif type(dst) == pcbnew.PCB_FIELD:
            # We have a destination but no source, so we delete the destination.
            if dst_fp:
                dst_fp.RemoveNative(dst)

        else:
            # We have neither a source nor a destination, so we do nothing.
            pass


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


def enforce_position(hd: HierarchicalData, board: pcbnew.BOARD):
    """Enforce the positions of objects in PCB template on PCB mutate."""
    # Prepare a lookup table for footprints in the board:
    # Since board.FindFootprintByPath() operates on a custom type that we can't easily
    # construct, we prepare a table for efficient string lookups instead.
    fp_lookup = {fp.GetPath().AsString(): fp for fp in board.GetFootprints()}

    errors: List[ReportedError] = []
    groupman: GroupManager = GroupManager(board)

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

            #Clear Volatile items first to prevent them from being orphaned
            clear_zones(board, group)
            clear_traces(board, group)
            clear_drawings(board, group)

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
            err_footprints = enforce_position_footprints(
                sheet, transform, fp_lookup, groupman.mover(group)
            )
            errors.extend(err_footprints)

            # Recreate traces:
            err_traces = copy_traces(board, sheet, transform, groupman.mover(group))
            errors.extend(err_traces)

            # Recreate Drawings
            err_drawings = copy_drawings(board,sheet,transform, groupman.mover(group))
            errors.extend(err_drawings)

            # Recreate Zones Currently Using Work around
            # zone.SetPosition() doesn't change position
            # for some reason?
            err_zones = copy_zones(board,sheet,transform, groupman.mover(group))
            errors.extend(err_zones)

    #Fixes issues with traces lingering after being deleted
    pcbnew.Refresh()


def clear_traces(board: pcbnew.BOARD, group: pcbnew.PCB_GROUP):
    """Remove all traces in a group."""

    # RunOnChildren/RunOnDescendants does not work for some reason, probably because the function
    # pointer type doesn't work in the Python bindings.

    for item in group.GetItems():
        if isinstance(item, (pcbnew.PCB_TRACK, pcbnew.ZONE)):
            board.RemoveNative(item)

        # TODO: Do we need to remove areas too?


def clear_drawings(board: pcbnew.BOARD, group: pcbnew.PCB_GROUP):
    """Remove all drawings in a group."""
    for item in group.GetItems():

        # Gets all drawings in a group
        if isinstance(item.Cast(), (pcbnew.PCB_SHAPE, pcbnew.PCB_TEXT)):
            # Remove every drawing
            board.RemoveNative(item)


def clear_zones(board: pcbnew.BOARD, group: pcbnew.PCB_GROUP):
    """Remove all zones in a group."""
    for item in group.GetItems():

        # Gets all drawings in a group
        if isinstance(item.Cast(), pcbnew.ZONE):
            # Remove every drawing
            board.RemoveNative(item)


def find_or_set_net(board: pcbnew.BOARD, net: pcbnew.NETINFO_ITEM):
    if existing_net := board.FindNet(net.GetNetname()):
        return existing_net
    else:
        return board.FindNet(0)


def copy_traces(
    board: pcbnew.BOARD,
    sheet: SchSheet,
    transform: PositionTransform,
    mover: GroupMoverType,
):
    # Instead of figuring out which nets are connected to the sub-PCB, we just copy all the raw traces
    # and let KiCad figure it out. It seems to work so far.

    errors = []
    for track in sheet.pcb.subboard.Tracks():
        # Copy track to trk:
        # logger.info(f"{track} {type(track)} {track.GetStart()} -> {track.GetEnd()}")
        
        trk = track.Duplicate()

        # Sets the track end point
        # the start is handled by item.SetPosition
        board.Add(trk)

        trk.SetNet(find_or_set_net(board, track.GetNet()))

        trk.SetStart(transform.translate(track.GetStart()))
        trk.SetEnd  (transform.translate(track.GetEnd()  ))

        if type(trk) == pcbnew.PCB_VIA:
            trk.SetIsFree(False)

        mover(trk)

    return errors


def copy_drawings(
    board: pcbnew.BOARD,
    sheet: SchSheet,
    transform: PositionTransform,
    mover: GroupMoverType,
):

    errors = []
    for drawing in sheet.pcb.subboard.GetDrawings():
        # if isinstance(drawing, pcbnew.PCB_SHAPE):
        #     newShape = pcbnew.PCB_SHAPE()
        # elif isinstance(drawing, pcbnew.PCB_TEXT):
        #     newShape = pcbnew.PCB_TEXT()   
        
        boardItem = drawing.Duplicate()

        board.Add(boardItem)

        # Set New Position
        boardItem.SetPosition(transform.translate(drawing.GetPosition()))

        # Drawings dont have .SetOrientation()
        # instead do a relative rotation
        boardItem.Rotate(boardItem.GetPosition(), transform.orient(pcbnew.ANGLE_0))

        mover(boardItem)

    return errors


def copy_zones(
    board: pcbnew.BOARD,
    sheet: SchSheet,
    transform: PositionTransform,
    mover: GroupMoverType,
):

    errors = []
    for zone in sheet.pcb.subboard.Zones():
        # if isinstance(drawing, pcbnew.PCB_SHAPE):
        #     newShape = pcbnew.PCB_SHAPE()
        # elif isinstance(drawing, pcbnew.PCB_TEXT):
        #     newShape = pcbnew.PCB_TEXT()   
        
        newZone = zone.Duplicate()

        board.Add(newZone)

        # Set New Position
        # newZone.SetPosition(transform.translate(zone.GetPosition()))
        # Temporary Workaround:
        
        # Move zone to 0,0 by moving relative
        newZone.Move(-newZone.GetPosition())
        # Move zone to correct location
        newZone.Move(transform.translate(zone.GetPosition()))

        # Drawings dont have .SetOrientation()
        # instead do a relative rotation
        newZone.Rotate(newZone.GetPosition(), transform.orient(pcbnew.ANGLE_0))

        mover(newZone)

    return errors


def enforce_position_footprints(
    sheet: SchSheet,
    transform: PositionTransform,
    fp_lookup: Dict[str, pcbnew.FOOTPRINT],
    groupmv: GroupMoverType,
):
    errors = []
    # For each footprint in the sub-PCB, find the corresponding footprint on the board:
    for fp in sheet.pcb.subboard.GetFootprints():
        # Find the corresponding footprint on the board:
        fp_path = sheet.identifier + fp.GetPath().AsString()
        fp_target = fp_lookup.get(fp_path)

        if not fp_target:
            errors.append(
                ReportedError(
                    "footprint not found, skipping",
                    message=f"Corresponding to {fp.GetReference()} for sheet {sheet.human_name}",
                    footprint=fp,
                    pcb=sheet.pcb,
                    level=ErrorLevel.WARNING,
                )
            )
            continue

        # TODO: Ignore footprints outside the lower-right quadrant.

        # Copy the properties and move the template to the target:
        transform.footprint(fp, fp_target)
        # Then move the text labels around:
        transform.footprint_text(fp.Reference(), fp_target.Reference())
        transform.footprint_text(fp.Value(), fp_target.Value())
        for pcb_field, fp_target_text in zip_longest(
            fp.GraphicalItems(), fp_target.GraphicalItems()
        ):
            # Provide the target footprint so that we can delete the text if necessary:
            transform.footprint_text(pcb_field, fp_target_text, fp_target)

        # Move the footprint into the group if one is provided:
        if groupmv(fp_target):
            errors.append(
                ReportedError(
                    f"footprint {fp_target} is in the wrong group",
                    pcb=sheet.pcb,
                    level=ErrorLevel.ERROR,
                )
            )

    return errors
