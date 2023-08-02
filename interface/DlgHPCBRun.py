import logging
from pathlib import Path
from typing import Dict
import wx

from .DlgHPCBRun_Base import DlgHPCBRun_Base
from ..hdata import HierarchicalData

logger = logging.getLogger("hierpcb")


class DlgHPCBRun(DlgHPCBRun_Base):
    def __init__(self, parent: wx.Window, hD: HierarchicalData):
        # Set up the user interface from the designer.
        super().__init__(parent)
        # Populate the dialog with data:
        self.hD = hD

        # imageList = wx.ImageList(16, 16)
        # icon_base = Path(__file__).resolve().parent
        # self.treeApplyTo.SetImageList(imageList)
        # ico_checked = imageList.Add(
        #     wx.Icon(str(icon_base / "checked.ico"), wx.BITMAP_TYPE_ICO)
        # )
        # ico_unchecked = imageList.Add(
        #     wx.Icon(str(icon_base / "unchecked.ico"), wx.BITMAP_TYPE_ICO)
        # )
        # ico_disabled = imageList.Add(
        #     wx.Icon(str(icon_base / "disabled.ico"), wx.BITMAP_TYPE_ICO)
        # )
        s_checked = "☑"
        s_unchecked = "☐"
        s_disabled = "☒"

        self.treeApplyTo.AppendColumn("Apply to")
        self.treeApplyTo.AppendColumn("sub-PCB", width=100)
        self.sheet_items: Dict[str, wx.TreeListItem] = {}
        for sheet in hD.root_sheet.tree_iter(skip_root=True):
            # Look up the parent, if it is in the tree already.
            parent_item: wx.TreeListItem = (
                self.sheet_items.get(sheet.parent.identifier, None)
                or self.treeApplyTo.GetRootItem()
            )
            item: wx.TreeListItem = self.treeApplyTo.AppendItem(
                parent=parent_item,
                text=sheet.human_name,
                data=sheet,
            )
            # If the sheet has a PCB, mention it in the appropriate column:
            sheet_pcb_text = s_checked + s_unchecked + s_disabled
            if sheet.pcb is not None:
                sheet_pcb_text = str(sheet.pcb.path.relative_to(hD.basedir))
                if not sheet.pcb.is_legal:
                    sheet_pcb_text = f"! {sheet_pcb_text}"

            self.treeApplyTo.SetItemText(item, 1, sheet_pcb_text)
            # Add the sheet to the tree, in case it is a future parent:
            self.sheet_items[sheet.identifier] = item

            # Expand the tree:
            self.treeApplyTo.Expand(item)
