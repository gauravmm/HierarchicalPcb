from itertools import zip_longest
import logging
import math
from typing import Dict, List, Optional, Tuple
from .hdata import HierarchicalData, PCBRoom, SchSheet

logger = logging.getLogger("hierpcb")

import pcbnew


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

    def abstract(
        self, pos_template: pcbnew.VECTOR2I, rot_template: float
    ) -> Tuple[pcbnew.VECTOR2I, float]:
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

        # And we also remember to rotate the footprint:
        new_rot: float = (
            rot_template
            - self.anchor_template.GetOrientation()
            + self.anchor_mutate.GetOrientation()
        )

        return pcbnew.VECTOR2I(int(new_x), int(new_y)), new_rot

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
        new_pos, new_rot = self.abstract(
            fp_template.GetPosition(), fp_template.GetOrientation()
        )
        fp_mutate.SetPosition(new_pos)
        fp_mutate.SetOrientation(new_rot)

    def footprint_text(
        self,
        src: Optional[pcbnew.FP_TEXT],
        dst: Optional[pcbnew.FP_TEXT],
        dst_fp: Optional[pcbnew.FOOTPRINT] = None,
    ):
        """Move dst to the same position as src, but relative to the anchor_mutate."""

        if type(src) == type(dst) == pcbnew.FP_TEXT:
            src.SetLayer(dst.GetLayer())
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

            # TODO: Set the flipped status

            # Move the text:
            new_pos, new_rot = self.abstract(src.GetPosition(), src.GetTextAngle())
            dst.SetPosition(new_pos)
            # The rotation stacks with the rotation of the footprint, so we don't need to
            # set the rotation here. TODO: Check this with a bunch of rotations.
            # dst.SetTextAngle(new_rot)

        elif type(src) == pcbnew.FP_TEXT:
            # We have a source but no destination. We should eventually add support for
            # creating a new text object, but not now.
            # TODO: Support creating text objects.
            pass

        elif type(dst) == pcbnew.FP_TEXT:
            # We have a destination but no source, so we delete the destination.
            if dst_fp:
                dst_fp.RemoveNative(dst)

        else:
            # We have neither a source nor a destination, so we do nothing.
            logger.debug("No source or destination text object: {dst} <- {src}")


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
                sheet, transform, fp_lookup, groupman, group
            )
            errors.extend(err_footprints)

            # Then, recreate the traces:
            pass


def enforce_position_footprints(
    sheet: SchSheet,
    transform: PositionTransform,
    fp_lookup: Dict[str, pcbnew.FOOTPRINT],
    groupman: GroupManager,
    group: Optional[pcbnew.PCB_GROUP],
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
        for fp_text, fp_target_text in zip_longest(
            fp.GraphicalItems(), fp_target.GraphicalItems()
        ):
            # Provide the target footprint so that we can delete the text if necessary:
            transform.footprint_text(fp_text, fp_target_text, fp_target)

        # Move the footprint into the group if one is provided:
        if groupman.move(fp_target, group):
            errors.append(
                ReportedError(
                    f"footprint {fp_target} is in the wrong group",
                    message=f"Expected group {group}",
                    pcb=sheet.pcb,
                    level=ErrorLevel.ERROR,
                )
            )

    return errors
