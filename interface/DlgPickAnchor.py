import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import wx
import pcbnew

from ..cfgman import ConfigMan
from ..hdata import HierarchicalData, SchSheet
from .DlgPickAnchor_Base import DlgPickAnchor_Base

logger = logging.getLogger("hierpcb")


class DlgPickAnchor(DlgPickAnchor_Base):
    def __init__(
        self,
        parent: wx.Window,
        options: List[pcbnew.FOOTPRINT],
        selected: Optional[str],
    ):
        # Set up the user interface from the designer.
        super().__init__(parent)
        self.options = sorted(options, key=lambda x: (-x.GetArea(), x.GetReference()))
        self.selection: Optional[str] = None

        # Populate the list of available footprints:
        presel: Optional[int] = None
        self.footprintList.AppendTextColumn("Reference")
        self.footprintList.AppendTextColumn("Footprint Size")
        for i, fp in enumerate(self.options):
            self.footprintList.AppendItem(
                [fp.GetReference(), f"{fp.GetArea():.2f} mm²"]
            )
            if fp.GetReference() == selected:
                presel = i

        # Select the default item:
        if presel:
            self.footprintList.SelectRow(presel)

    def selectionChanged(self, event):
        selRow = self.footprintList.GetSelectedRow()
        if selRow != wx.NOT_FOUND:
            fp = self.options[selRow]
            self.selection = fp.GetReference()
        else:
            event.Veto()

    def submitForm(self, event):
        """Handle a click on a tree item."""
        selRow = self.footprintList.GetSelectedRow()
        if selRow != wx.NOT_FOUND:
            fp = self.options[selRow]
            self.selection = fp.GetReference()
            self.EndModal()
        else:
            event.Veto()
