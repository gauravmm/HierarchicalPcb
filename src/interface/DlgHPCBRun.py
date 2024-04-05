import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import wx

from ..cfgman import ConfigMan
from ..hdata import HierarchicalData, PCBRoom, SchSheet
from .DlgHPCBRun_Base import DlgHPCBRun_Base

logger = logging.getLogger("hierpcb")


def setItemPrefix(tree: wx.dataview.TreeListCtrl, item: wx.dataview.TreeListItem, prefix: str):
    prefixes = ["✅", "❌"]
    """Set the prefix of the item's text and remove the previous prefix if any (always separated by a space)."""
    if prefix not in prefixes:
        raise ValueError(f"Invalid prefix: {prefix}")
    text = tree.GetItemText(item)
    for p in prefixes:
        text = text.replace(f"{p} ", "")
    tree.SetItemText(item, f"{prefix} {text}")

def setItemChecked(tree: wx.dataview.TreeListCtrl, item: wx.dataview.TreeListItem, checked: bool):
    """Set the checked state of the item."""
    setItemPrefix(tree, item, '✅' if checked else '❌')

def set_checked_default(
    tree: wx.dataview.TreeListCtrl, sheet: SchSheet
):
    """Set the tree to its default state starting from node `sheet`."""

    sheet.checked = False
    # Skip nodes that don't have list refs:
    if sheet.list_ref:
        # Check if the sheet has a PCB:
        if sheet.pcb and sheet.pcb.is_legal:
            # If an ancestor is checked, this sheet cannot be checked.
            # Otherwise, this is the first sheet from the root to be elligible,
            sheet.checked = True

        setItemChecked(tree, sheet.list_ref, sheet.checked)


def apply_checked(tree: wx.dataview.TreeListCtrl, sheet: SchSheet):
    """Mutate the tree to reflect the checked state of the sheets."""
    # Skip nodes that don't have list refs:
    if sheet.list_ref:
        setItemChecked(tree, sheet.list_ref, sheet.checked)


def is_checkable(tree: wx.dataview.TreeListCtrl, sheet: SchSheet) -> bool:
    """Check if the sheet may be checked."""
    if sheet.pcb and sheet.pcb.is_legal:
        # Now that we know it can be checked, verify that no ancestor is checked:
        node = sheet.parent
        while node is not None and node.list_ref is not None:
            logger.info(f"Checking {node.identifier}: {node.checked}.")
            if node.checked:
                return False
            node = node.parent
        return True
    return False


class DlgHPCBRun(DlgHPCBRun_Base):
    def __init__(self, cfg: ConfigMan, parent: wx.Window, hD: HierarchicalData):
        # Set up the user interface from the designer.
        super().__init__(parent)
        # Populate the dialog with data:
        self.hD = hD

        #Create the root or else our first added layout will be
        root_item: wx.TreeListItem = self.treeApplyTo.AddRoot(
            text=""
        )
        
        pcbDict = {}
        labels = {}
        for sheet in hD.root_sheet.children.values():
            # If the sheet has a PCB, mention it in the appropriate column:
            row_text = sheet.human_name
            pcbDict.setdefault(sheet.pcb, []).append(sheet)

            if sheet.pcb is not None:
                if not sheet.pcb.is_legal:
                    row_text += " No Footprints!"
            labels[sheet] = row_text
        
        for pcb in pcbDict:
            if pcb and pcb.is_legal:
                pcb_group_item: wx.TreeListItem = self.treeApplyTo.PrependItem(
                    parent=root_item, text=f"{pcb.path.relative_to(hD.basedir)}:"
                )
            else:
                pcb_group_item: wx.TreeListItem = self.treeApplyTo.AppendItem(
                    parent=root_item, text="Invalid PCB:", 
                )

            pcbDict[pcb] = humanSort(pcbDict[pcb], key=lambda x: labels[x])

            # Populate the Pcb with it's corrosponding sheets
            for sheet in pcbDict[pcb]:
                item: wx.TreeListItem = self.treeApplyTo.AppendItem(
                    parent=pcb_group_item or invalid_item , text=labels[sheet], data=sheet
                )

                # Pass a reference item to the sheet:
                sheet.list_ref = item

                # Set the default state of the tree:
                if pcb and pcb.is_legal:
                    apply_checked(self.treeApplyTo, sheet)

        self.treeApplyTo.ExpandAll()

        # Populate the list of available sub-PCBs:
        self.subPCBList.AppendTextColumn("Name")
        self.subPCBList.AppendTextColumn("Anchor Footprint")
        self.pcb_rooms_lookup = [subpcb for _, subpcb in sorted(hD.pcb_rooms.items())]
        for subpcb in self.pcb_rooms_lookup:
            self.subPCBList.AppendItem([subpcb.path.name, subpcb.get_anchor_ref()])

    def handleSelection(self, evt: wx.dataview.TreeListEvent):
        """Handle a click on a tree item."""
        item = evt.GetItem()
        # Get the sheet associated with the item:
        sheet: SchSheet = self.treeApplyTo.GetItemData(item)
        # If the sheet is now unchecked, do nothing:

        if is_checkable(self.treeApplyTo, sheet):
            if sheet.checked:
                sheet.checked = False
                setItemChecked(self.treeApplyTo, item, False)
            else:
                # Check it and uncheck all descendants:
                set_checked_default(self.treeApplyTo, sheet)

    def resetToDefault(self, event):
        """Reset the tree to its default state."""
        set_checked_default(self.treeApplyTo, self.hD.root_sheet)

    def getSelectedSubPCB(self) -> Optional[PCBRoom]:
        selRow = self.subPCBList.GetSelectedRow()
        try:
            subpcb: PCBRoom = self.pcb_rooms_lookup[selRow]
            logger.info(f"Selected for {selRow} : {subpcb.path}")
            return subpcb
        except IndexError:
            logger.info(f"Invalid index: {selRow}")
            return None

    def changeSelectedSubPCB(self, event):
        """Update the choices of anchors for the selected sub-PCB."""
        # Get the selected sub-PCB:
        subpcb = self.getSelectedSubPCB()
        if subpcb is None:
            return

        # Get the current selection
        curr = subpcb.get_anchor_ref() or subpcb.get_heuristic_anchor_ref()
        # Get the list of available anchors:
        self.anchors = sorted(subpcb.get_anchor_refs().values())
        logger.info(f"Anchors  ({curr}): {self.anchors}")
        self.anchorChoice.Clear()
        self.anchorChoice.AppendItems(self.anchors)
        # Select the current anchor:
        self.anchorChoice.SetSelection(self.anchors.index(curr))

    def changeAnchor(self, event):
        # Set the anchor:
        subpcb = self.getSelectedSubPCB()
        if subpcb is None:
            return

        # Get the selected anchor:
        sel = self.anchorChoice.GetSelection()
        logger.info(f"Anchor {sel} for {subpcb.path}")
        if sel == wx.NOT_FOUND:
            logger.warning("No anchor selected!")
            return

        sel_ref = self.anchors[sel]
        subpcb.set_anchor_ref(sel_ref)
        # Update the display:
        self.subPCBList.SetTextValue(sel_ref, self.subPCBList.GetSelectedRow(), 1)

    def handleApply(self, event):
        """Submit the form."""
        # Mutate the tree structure and
        self.EndModal(wx.ID_OK)


def humanSort(list, key=None):
    '''Sort the given list of strings in the way that humans expect (e.g. "1" < "2" < "10"). Also support all string prefixes and sort those alphabetically like a1 < a11 < b3 < b20'''
    import re
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ]
    if key:
        list.sort(key=lambda x: alphanum_key(key(x)))
    else:
        list.sort(key=alphanum_key)
    return list
