import wx

from .DlgHPCBRun_Base import DlgHPCBRun_Base


class DlgHPCBRun(DlgHPCBRun_Base):
    def __init__(self, parent: wx.Window):
        DlgHPCBRun_Base.__init__(self, parent)
