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
## Class DlgPickAnchor_Base
###########################################################################


class DlgPickAnchor_Base(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(
            self,
            parent,
            id=wx.ID_ANY,
            title=wx.EmptyString,
            pos=wx.DefaultPosition,
            size=wx.Size(376, 396),
            style=wx.DEFAULT_DIALOG_STYLE,
        )

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        bSizer7 = wx.BoxSizer(wx.VERTICAL)

        self.footprintList = wx.dataview.DataViewListCtrl(
            self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0
        )
        bSizer7.Add(self.footprintList, 1, wx.ALL | wx.EXPAND, 5)

        m_sdbSizer2 = wx.StdDialogButtonSizer()
        self.m_sdbSizer2OK = wx.Button(self, wx.ID_OK)
        m_sdbSizer2.AddButton(self.m_sdbSizer2OK)
        self.m_sdbSizer2Cancel = wx.Button(self, wx.ID_CANCEL)
        m_sdbSizer2.AddButton(self.m_sdbSizer2Cancel)
        m_sdbSizer2.Realize()

        bSizer7.Add(m_sdbSizer2, 0, wx.EXPAND, 5)

        self.SetSizer(bSizer7)
        self.Layout()

        self.Centre(wx.BOTH)

        # Connect Events
        self.footprintList.Bind(
            wx.dataview.EVT_DATAVIEW_SELECTION_CHANGED,
            self.selectionChanged,
            id=wx.ID_ANY,
        )
        self.footprintList.Bind(wx.EVT_LEFT_DCLICK, self.submitForm)

    def __del__(self):
        pass

    # Virtual event handlers, override them in your derived class
    def selectionChanged(self, event):
        event.Skip()

    def submitForm(self, event):
        event.Skip()
