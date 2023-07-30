import logging
import os
import sys
from pathlib import Path

from .hdata import HierarchicalData

import pcbnew
import wx

logger = logging.getLogger("hierpcb")


class HierarchicalPCBPlugin(pcbnew.ActionPlugin):
    def __init__(self):
        super().__init__()
        self.version = "0.0.1"

    def defaults(self):
        self.name = "HierarchicalPCB"
        self.category = "Layout"
        self.description = (
            "True hierarchical layouts to go with the hierarchical schematics."
            "You can define 'rooms' for different schematics throughout the hierarchy"
            "and this plugin will enforce them on the PCB."
        )
        self.icon_file_name = str(Path(__file__).parent / "icon.png")
        self.show_toolbar_button = True

    def Run(self):
        # grab PCB editor frame
        wx_frame = wx.FindWindowByName("PcbFrame")
        board = pcbnew.GetBoard()

        if not logger.handlers:
            logger.addHandler(
                logging.FileHandler(
                    filename=board.GetFileName() + ".hierpcb.log",
                    mode="w",
                )
            )

        # set up logger
        logger.info(
            f"Plugin v{self.version} running on KiCad {pcbnew.GetBuildVersion()} and Python {sys.version} on {sys.platform}."
        )

        hD = HierarchicalData(board)
        logger.info(hD.sheets)
