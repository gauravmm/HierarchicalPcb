# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version 3.10.1-0-g8feb16b3)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc
import wx.dataview

###########################################################################
## Class DlgHPCBRun_Base
###########################################################################


class DlgHPCBRun_Base(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(
            self,
            parent,
            id=wx.ID_ANY,
            title="HierarchicalPCB",
            pos=wx.DefaultPosition,
            size=wx.Size(465, 788),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        bSizerMain = wx.BoxSizer(wx.VERTICAL)

        bSizerMain.SetMinSize(wx.Size(-1, 600))
        self.m_staticText1 = wx.StaticText(
            self,
            wx.ID_ANY,
            "Choose which sub-PCB layouts to apply:",
            wx.DefaultPosition,
            wx.DefaultSize,
            0,
        )
        self.m_staticText1.Wrap(-1)

        bSizerMain.Add(self.m_staticText1, 0, wx.ALL, 5)

        self.treeApplyTo = wx.dataview.TreeListCtrl(
            self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.dataview.TL_SINGLE
        )
        self.treeApplyTo.SetMinSize(wx.Size(-1, 300))

        bSizerMain.Add(self.treeApplyTo, 1, wx.ALL | wx.EXPAND, 5)

        self.m_staticText41 = wx.StaticText(
            self, wx.ID_ANY, "Reset to Default", wx.DefaultPosition, wx.DefaultSize, 0
        )
        self.m_staticText41.Wrap(-1)

        self.m_staticText41.SetFont(
            wx.Font(
                wx.NORMAL_FONT.GetPointSize(),
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                True,
                wx.EmptyString,
            )
        )
        self.m_staticText41.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
        )
        self.m_staticText41.SetToolTip(
            "The anchor is the component in each sub-PCB around which all others are arranged. You must set the anchor to a component with a unique prefix.\n"
        )

        bSizerMain.Add(self.m_staticText41, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.m_staticline1 = wx.StaticLine(
            self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL
        )
        bSizerMain.Add(self.m_staticline1, 0, wx.EXPAND | wx.ALL, 5)

        self.m_staticText2 = wx.StaticText(
            self,
            wx.ID_ANY,
            "Configure each sub-PCB layout:",
            wx.DefaultPosition,
            wx.DefaultSize,
            0,
        )
        self.m_staticText2.Wrap(-1)

        bSizerMain.Add(self.m_staticText2, 0, wx.ALL, 5)

        self.m_scrolledWindowApplyTo1 = wx.ScrolledWindow(
            self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.VSCROLL
        )
        self.m_scrolledWindowApplyTo1.SetScrollRate(5, 5)
        self.m_scrolledWindowApplyTo1.SetMinSize(wx.Size(-1, 200))

        bSizer31 = wx.BoxSizer(wx.VERTICAL)

        self.m_dataViewListCtrl1 = wx.dataview.DataViewListCtrl(
            self.m_scrolledWindowApplyTo1,
            wx.ID_ANY,
            wx.DefaultPosition,
            wx.DefaultSize,
            0,
        )
        self.m_dataViewListCtrl1.SetMinSize(wx.Size(-1, 200))

        bSizer31.Add(self.m_dataViewListCtrl1, 1, wx.EXPAND, 5)

        self.m_scrolledWindowApplyTo1.SetSizer(bSizer31)
        self.m_scrolledWindowApplyTo1.Layout()
        bSizer31.Fit(self.m_scrolledWindowApplyTo1)
        bSizerMain.Add(self.m_scrolledWindowApplyTo1, 1, wx.EXPAND, 5)

        bSizer4 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_panel2 = wx.Panel(
            self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL
        )
        bSizer4.Add(self.m_panel2, 1, wx.EXPAND | wx.ALL, 5)

        self.m_staticText5 = wx.StaticText(
            self, wx.ID_ANY, "Help:", wx.DefaultPosition, wx.DefaultSize, 0
        )
        self.m_staticText5.Wrap(-1)

        bSizer4.Add(self.m_staticText5, 0, wx.ALL, 5)

        self.m_staticText4 = wx.StaticText(
            self, wx.ID_ANY, "Anchors", wx.DefaultPosition, wx.DefaultSize, 0
        )
        self.m_staticText4.Wrap(-1)

        self.m_staticText4.SetFont(
            wx.Font(
                wx.NORMAL_FONT.GetPointSize(),
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                True,
                wx.EmptyString,
            )
        )
        self.m_staticText4.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
        )
        self.m_staticText4.SetToolTip(
            "The anchor is the component in each sub-PCB around which all others are arranged."
        )

        bSizer4.Add(self.m_staticText4, 0, wx.ALL, 5)

        bSizerMain.Add(bSizer4, 0, wx.EXPAND, 5)

        self.m_staticline2 = wx.StaticLine(
            self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL
        )
        bSizerMain.Add(self.m_staticline2, 0, wx.EXPAND | wx.ALL, 5)

        m_sdbSizer1 = wx.StdDialogButtonSizer()
        self.m_sdbSizer1Apply = wx.Button(self, wx.ID_APPLY)
        m_sdbSizer1.AddButton(self.m_sdbSizer1Apply)
        self.m_sdbSizer1Cancel = wx.Button(self, wx.ID_CANCEL)
        m_sdbSizer1.AddButton(self.m_sdbSizer1Cancel)
        m_sdbSizer1.Realize()

        bSizerMain.Add(m_sdbSizer1, 0, wx.EXPAND, 5)

        self.SetSizer(bSizerMain)
        self.Layout()

        self.Centre(wx.BOTH)

    def __del__(self):
        pass
