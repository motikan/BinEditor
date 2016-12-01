#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import sys
import wx
import wx.lib.agw.genericmessagedialog as gmd
from hex_editor import HexEditor
from hex_grid_table import HexGridTable
from valid_types import VALID_TYPES
from search_types import SEARCH_TYPES


if sys.version_info[:2] < (2, 7):
  def bin(number):
    if number == 0:
      return ''
    else:
      return bin(number / 2) + str(number % 2)

class HexEditorFrame(wx.Frame):

  def __init__(self, parent):
    wx.Frame.__init__(self, id=-1, name='',
      parent=parent, title="HexEditor", size=(720, 700))
    sizer = wx.BoxSizer(wx.VERTICAL)

    self.editor = HexEditor(self)

    sizer.Add(self.editor, 1, wx.EXPAND)
    self.SetSizer(sizer)

    self.CenterOnScreen()

  def OpenFile(self, filename):
      self.editor.LoadFile(filename)

class HexEditorApp(wx.App):

  def OnInit(self):
    self.mainFrame = HexEditorFrame(None)
    self.mainFrame.Show()
    self.SetTopWindow(self.mainFrame)
    return True

  def main(*args):
    application = HexEditorApp(None)
    if len(args[0]) > 1 and os.path.isfile(args[0][1]):
      application.OpenFile(filename=args[0][1])
      application.MainLoop()

  def OpenFile(self, filename=''):
    if filename:
      self.mainFrame.OpenFile(filename)

# スクリプトから実行用
def OpenEditor(input_filename):
  application = HexEditorApp(None)
  application.OpenFile(filename=input_filename)
  application.MainLoop()

# コマンドから実行用
if __name__ == '__main__':
  import sys
  HexEditorApp.main(sys.argv)
