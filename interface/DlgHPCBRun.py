import logging
from pathlib import Path
from typing import Any, Callable, Dict
import wx

from .DlgHPCBRun_Base import DlgHPCBRun_Base
from ..hdata import HierarchicalData, SchSheet

logger = logging.getLogger("hierpcb")


def set_checked_default(
    tree: wx.dataview.TreeListCtrl, sheet: SchSheet, ancestor_checked: bool = False
):
    """Set the tree to its default state starting from node `sheet`."""

    checked = False
    # Skip nodes that don't have list refs:
    if sheet.list_ref:
        # Check if the sheet has a PCB:
        if sheet.pcb and sheet.pcb.is_legal:
            # If an ancestor is checked, this sheet cannot be checked.
            # Otherwise, this is the first sheet from the root to be elligible,
            if not ancestor_checked:
                checked = True

        tree.CheckItem(sheet.list_ref, wx.CHK_CHECKED if checked else wx.CHK_UNCHECKED)

    # Recur on the children:
    for _, child in sorted(sheet.children.items()):
        set_checked_default(tree, child, checked or ancestor_checked)


def is_checkable(tree: wx.dataview.TreeListCtrl, sheet: SchSheet) -> bool:
    """Check if the sheet may be checked."""
    if sheet.pcb is None or not sheet.pcb.is_legal:
        return False

    # Now that we know it can be checked, verify that no ancestor is checked:
    node = sheet.parent
    while node is not None and node.list_ref is not None:
        if tree.IsItemChecked(node.list_ref):
            return False
        node = node.parent


class DlgHPCBRun(DlgHPCBRun_Base):
    def __init__(self, parent: wx.Window, hD: HierarchicalData):
        # Set up the user interface from the designer.
        super().__init__(parent)
        # Populate the dialog with data:
        self.hD = hD

        # Set up the event handlers:
        def handle_checked(evt: wx.dataview.TreeListEvent):
            """Handle a click on a tree item."""
            item = evt.GetItem()
            # Get the sheet associated with the item:
            sheet: SchSheet = self.treeApplyTo.GetItemData(item)
            # If the sheet is now unchecked, do nothing:
            checked = self.treeApplyTo.IsItemChecked(item)

            logger.info(f"Checked {sheet.human_name}: {checked}")

            if not checked:
                pass

            elif not is_checkable(self.treeApplyTo, sheet):
                # If the sheet is not checkable, uncheck it:
                self.treeApplyTo.CheckItem(sheet.list_ref, wx.CHK_UNCHECKED)

            else:
                # Now we know the sheet is checkable, so we check it and uncheck all descendants:
                set_checked_default(self.treeApplyTo, sheet, ancestor_checked=False)

        self.treeApplyTo.AppendColumn("Apply to")
        self.treeApplyTo.AppendColumn("sub-PCB", width=100)
        for sheet in hD.root_sheet.tree_iter(skip_root=True):
            # Look up the parent, if it is in the tree already.
            parent_item: wx.TreeListItem = (
                sheet.parent.list_ref or self.treeApplyTo.GetRootItem()
            )
            item: wx.TreeListItem = self.treeApplyTo.AppendItem(
                parent=parent_item,
                text=sheet.human_name,
                data=sheet,
            )
            # If the sheet has a PCB, mention it in the appropriate column:
            sheet_pcb_text = ""
            if sheet.pcb is not None:
                sheet_pcb_text = str(sheet.pcb.path.relative_to(hD.basedir))
                if not sheet.pcb.is_legal:
                    sheet_pcb_text = f"No Footprints! {sheet_pcb_text}"

            self.treeApplyTo.SetItemText(item, 1, sheet_pcb_text)
            # Add the sheet to the tree, in case it is a future parent:
            sheet.list_ref = item

            # Expand the tree:
            self.treeApplyTo.Expand(item)

        # Set the default state of the tree:
        set_checked_default(self.treeApplyTo, hD.root_sheet)

        self.treeApplyTo.Bind(wx.dataview.EVT_TREELIST_ITEM_CHECKED, handle_checked)
