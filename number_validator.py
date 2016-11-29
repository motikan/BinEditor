# -*- coding: utf-8 -*-
import wx

class NumberValidator(wx.PyValidator):

    def __init__(self, allow_chars):
        #wx.PyValidator.__init__(self)
        wx.Validator.__init__(self)
        self.allow_chars = allow_chars
        self.Bind(wx.EVT_CHAR, self.OnChar)

    def Clone(self):
        return NumberValidator(self.allow_chars)

    def Validate(self, win):
        val = win.GetValue()
        for char in val:
            if char not in self.allow_chars:
                return False
        return True

    def OnChar(self, event):
        key = event.GetKeyCode()

        if key < wx.WXK_SPACE or key == wx.WXK_DELETE or key > 255:
            event.Skip()
            return

        if chr(key) in self.allow_chars:
            event.Skip()

        return