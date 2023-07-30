import logging
import os
from HierarchicalPcb import hierarchical
import wx
import pcbnew
from pathlib import Path

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(lineno)d:%(message)s",
    datefmt="%m-%d %H:%M:%S",
)
logger = logging.getLogger("hierpcb")


class HierarchicalPCB(pcbnew.ActionPlugin):
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
        self.icon_file_name = Path(__file__).parent / "icon.png"
        self.show_toolbar_button = True

    def Run(self):
        # grab PCB editor frame
        wx_frame = wx.FindWindowByName("PcbFrame")
        board = pcbnew.GetBoard()

        # go to the project folder - so that log will be in proper place
        os.chdir()

        if not logger.handlers:
            logger.addHandler(
                logging.FileHandler(
                    filename=Path(board.GetFileName()).parent / "hierarchical.log",
                    mode="w",
                )
            )

        # set up logger
        logger.info(
            f"Plugin {self.version} running on KiCad {pcbnew.GetBuildVersion()} and Python {sys.version} on {sys.platform}."
        )

        hierarchical.get_footprints_by_sheet(board)
