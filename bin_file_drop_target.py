# -*- coding: utf-8 -*-
import wx
import os


class BinFileDropTarget(wx.FileDropTarget):
  def __init__(self, editor):
    wx.FileDropTarget.__init__(self)
    self.editor = editor

  def OnDropFiles(self, x, y, filenames):
    filenames = [path for path in filenames if os.path.isfile(path)]
    self.editor.LoadFile(filenames[0])
