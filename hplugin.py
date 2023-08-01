import logging
import os
import pprint
import sys
import time
import traceback
from pathlib import Path

import pcbnew
import wx

from .hdata import HierarchicalData
from .interface import DlgHPCBRun

logger = logging.getLogger("hierpcb")
logger.setLevel(logging.DEBUG)


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
        self.RunActual()

    def RunActual(self):
        # grab PCB editor frame
        wx_frame = wx.FindWindowByName("PcbFrame")
        board = pcbnew.GetBoard()

        for lH in list(logger.handlers):
            logger.removeHandler(lH)
        logger.addHandler(
            logging.FileHandler(filename=board.GetFileName() + ".hierpcb.log", mode="w")
        )

        # set up logger
        logger.info(
            f"Plugin v{self.version} running on KiCad {pcbnew.GetBuildVersion()} and Python {sys.version} on {sys.platform}."
        )

        hD = HierarchicalData(board)
        logger.debug(hD.root_sheet)

        rv = DlgHPCBRun(wx_frame, hD).ShowModal()
        logger.info(rv)
