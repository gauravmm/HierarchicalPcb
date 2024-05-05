import logging
import os
import pprint
import sys
import time
import traceback
from pathlib import Path

import pcbnew
import wx

from .cfgman import ConfigMan
from .hdata import HierarchicalData
from .interface import DlgHPCBRun
from .placement import enforce_position

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
            "You can define 'rooms' for different schematics throughout the hierarchy "
            "and this plugin will enforce them on the PCB."
        )
        self.icon_file_name = str(Path(__file__).parent / "icon.png")
        self.show_toolbar_button = True

    def Run(self):
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

        with ConfigMan(Path(board.GetFileName() + ".hierpcb.json")) as cfg:
            RunActual(cfg, wx_frame, board)


def RunActual(cfg: ConfigMan, wx_frame: wx.Window, board: pcbnew.BOARD):
    hD = HierarchicalData(board)
    logger.debug(str(hD.root_sheet))
    for room in hD.pcb_rooms.values():
        logger.debug(str(room))
    hD.load(cfg)  # Load defaults

    if DlgHPCBRun(cfg, wx_frame, hD).ShowModal() == wx.ID_OK:
        enforce_position(hD, board)

        hD.save(cfg)
        logger.info("Saved.")
