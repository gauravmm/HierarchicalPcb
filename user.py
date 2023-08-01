"""User interactions with the plugin.
"""
import wx

from .interface import DlgHPCBRun


def show_run_dialog(frame: wx.Window):
    """Show the main dialog for the plugin."""
    dlg = DlgHPCBRun()
    dlg.ShowModal()
