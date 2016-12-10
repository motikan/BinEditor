# -*- coding: utf-8 -*-
import os
import wx
import struct
import re
import wx.lib.agw.buttonpanel as btnpanel
import wx.grid as wxgrid
import wx.lib.agw.genericmessagedialog as gmd
from transparent_text import TransparentText
from number_validator import NumberValidator
from valid_types import VALID_TYPES
from search_types import SEARCH_TYPES
from hex_grid_table import HexGridTable
from bin_file_drop_target import BinFileDropTarget


class HexEditor(wx.Panel):

    def __init__(self, parent, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)

        self.__init_ctrls(parent)

        self.Binary = "\x00" * 0x100

        self.SetDropTarget(BinFileDropTarget(self))

    def __init_ctrls(self, parent):

        self.SetFont(wx.Font(9, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, 
            wx.FONTWEIGHT_NORMAL, False, "Courier New"))

        sizer = wx.BoxSizer(wx.VERTICAL)

        # ツールバー
        self.toolbar = self.__init_toolbar()
        sizer.Add(self.toolbar, 0, wx.EXPAND)

        # 検索バー
        self.find_bar = self.__init_find_bar()
        sizer.Add(self.find_bar, 0, wx.EXPAND)

        # hexエディタ部分
        self._grid_selecting_start = False
        self._in_selecting = False
        self.grid = wxgrid.Grid(self, -1)
        self._hex_cols = 16
        self._init_grid()
        self._reset_grid()
        sizer.Add(self.grid, 1, wx.EXPAND)

        # ステータスバー
        self.status_bar = self.__init_status_bar()
        sizer.Add(self.status_bar, 0, wx.EXPAND)

        self.Bind(wx.EVT_SIZE, self.AutoSize)

        self.SetSizer(sizer)

    # ツールバー
    def __init_toolbar(self):
        toolbar = btnpanel.ButtonPanel(self, -1, "", btnpanel.BP_DEFAULT_STYLE)

        toolbar.AddControl(TransparentText(toolbar, -1, "Current Addr:", size=(-1, -1)))
        self._current_text = wx.TextCtrl(toolbar, -1,
                                         size=(80, 20),
                                         style=wx.TE_PROCESS_ENTER | wx.TE_RIGHT,
                                         validator=NumberValidator(VALID_TYPES.HEX_CHARS))
        self._current_text.Bind(wx.EVT_KEY_DOWN, self.OnCurrentKeyDown)
        toolbar.AddControl(self._current_text)

        toolbar.AddSeparator()

        toolbar.AddControl(TransparentText(toolbar, -1, "Value:", size=(-1, -1)))
        self._value_hex = wx.TextCtrl(toolbar, -1,
                                      size=(30, 20),
                                      style=wx.TE_PROCESS_ENTER | wx.TE_RIGHT,
                                      validator=NumberValidator(VALID_TYPES.HEX_CHARS))
        self._value_hex.SetMaxLength(2)
        self._value_dec = wx.TextCtrl(toolbar, -1,
                                      size=(40, 20),
                                      style=wx.TE_PROCESS_ENTER | wx.TE_RIGHT,
                                      validator=NumberValidator(VALID_TYPES.DEC_CHARS))
        self._value_dec.SetMaxLength(3)
        self._value_bin = wx.TextCtrl(toolbar, -1,
                                      size=(80, 20),
                                      style=wx.TE_PROCESS_ENTER | wx.TE_RIGHT,
                                      validator=NumberValidator(VALID_TYPES.BIN_CHARS))
        self._value_bin.SetMaxLength(8)
        self._value_chr = TransparentText(toolbar, -1, " ", size=(-1, -1))
        toolbar.AddControl(self._value_hex)
        toolbar.AddControl(self._value_dec)
        toolbar.AddControl(self._value_bin)
        self._value_hex.Bind(wx.EVT_CHAR, self.OnValueTextChar)
        self._value_dec.Bind(wx.EVT_CHAR, self.OnValueTextChar)
        self._value_bin.Bind(wx.EVT_CHAR, self.OnValueTextChar)
        toolbar.AddControl(self._value_chr)

        toolbar.AddSeparator()
        self.menu = self._init_grid_menu(True)
        btn_menu = wx.Button(toolbar, label=u"\u25BC", size=(20, 20))
        toolbar.Bind(wx.EVT_BUTTON, self.OnMenuButton, id=btn_menu.GetId())
        toolbar.AddControl(btn_menu)

        btn_menu2 = wx.Button(toolbar, label=u"送信", size=(60, 20))
        toolbar.Bind(wx.EVT_BUTTON, self.OnTransmissionButton, id=btn_menu2.GetId())
        toolbar.AddControl(btn_menu2)

        toolbar.DoLayout()
        return toolbar

    # 検索バー
    def __init_find_bar(self):
        find_bar = btnpanel.ButtonPanel(self, -1, "", btnpanel.BP_DEFAULT_STYLE)

        find_bar.AddControl(TransparentText(find_bar, -1, "Search:", size=(-1, -1)))
        self._find_text = wx.TextCtrl(find_bar, -1,
                                      size=(220, 20),
                                      style=wx.TE_PROCESS_ENTER)
        self._find_text.Bind(wx.EVT_KEY_DOWN, self.OnFindKeyDown)
        find_bar.AddControl(self._find_text)

        btn_find = wx.Button(find_bar, label="Find", size=(40, 22))
        find_bar.Bind(wx.EVT_BUTTON, self.OnFindButton, id=btn_find.GetId())
        find_bar.AddControl(btn_find)

        self.find_types = []
        for find_type in SEARCH_TYPES.Values():
            radio = wx.RadioButton(find_bar, -1, find_type)
            find_bar.AddControl(radio)
            self.find_types.append(radio)
        self.find_types[0].SetValue(True)

        self._search_options = {}
        self._search_result = None

        find_bar.DoLayout()
        return find_bar

    def _init_grid(self):
        self.grid.CreateGrid(0, 0)
        self.grid.SetDefaultCellAlignment(wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)
        self.grid.SetRowLabelAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
        self.grid.SetDefaultColSize(26)
        self.grid.DisableDragColSize()
        self.grid.DisableDragRowSize()
        #self.grid.SetLabelBackgroundColour("#E2E8F0")

        corner = self.grid.GetGridCornerLabelWindow()
        addr = wx.StaticText(corner, label="Address", pos=(20, 12))
        corner.Bind(wx.EVT_LEFT_DOWN, lambda e: self.SetSelection(0, self.Length, False))
        addr.Bind(wx.EVT_LEFT_DOWN, lambda e: self.SetSelection(0, self.Length, False))

        self._grid_menu = self._init_grid_menu(False)

        self.grid.Bind(wx.EVT_KEY_DOWN, self.OnGridKeyDown)
        self.grid.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.OnSelectCell)
        self.grid.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnCellRightClicked)
        self.grid.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK, self.OnCellRightClicked)

        self.grid.GetGridColLabelWindow().Bind(wx.EVT_LEFT_DOWN, self.OnGridColLeftDown)
        self.grid.GetGridWindow().Bind(wx.EVT_LEFT_DOWN, self.OnGridLeftDown)
        self.grid.GetGridWindow().Bind(wx.EVT_LEFT_UP, self.OnGridLeftUp)
        self.grid.GetGridWindow().Bind(wx.EVT_MOTION, self.OnGridLeftMotion)
        self.grid.GetGridRowLabelWindow().Bind(wx.EVT_MOTION, self.OnGridLeftMotion)
        self.grid.GetGridRowLabelWindow().Bind(wx.EVT_LEFT_UP, self.OnGridRowLeftUp)

    def _reset_grid(self):
        self.grid.ClearGrid()
        self._reset_grid_selecting()

    def AutoSize(self, event=None):
        size = self.GetSize()
        sb_width = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
        col_size = (size[0] - 150 - sb_width - self.grid.GetRowLabelSize()) / self.HexCols
        if col_size < -1:
            col_size = -1
        for col in range(self.grid.GetNumberCols() - 1):
            self.grid.SetColSize(col, col_size)
        self.grid.SetColSize(self.grid.GetNumberCols() - 1, 140)
        self.grid.Refresh()
        event and event.Skip()

    def _init_grid_menu(self, main_menu=False):
        menu = wx.Menu()
        if main_menu:
            items = [
                ("New", lambda e: self.NewDialog()),
                ("Load", lambda e: self.OpenFileDialog()),
                ("Save", lambda e: self.SaveFileDialog()),
            ]
        else:
            items = [
                ("Cut", lambda e: self._cut()),
                ("Copy", lambda e: self._copy()),
                ("Paste", lambda e: self._paste()),
                ("Insert", lambda e: self._insert()),
                "-",
                ("Undo", lambda e: self.Undo()),
                ("Redo", lambda e: self.Redo()),
                "-",
                ("Delete", lambda e: self._delete()),
                ("Select All", lambda e: self.SetSelection(0, self.Length, False)),
            ]
        for item in items:
            if item == "-":
                menu.AppendSeparator()
            else:
                name, func = item
                menu_id = wx.NewId()
                menu.Append(menu_id, name)
                self.Bind(wx.EVT_MENU, func, id=menu_id)

        return menu

    def __init_status_bar(self):
        sb = wx.StatusBar(self)
        sb.SetFieldsCount(4)
        sb.SetStatusWidths([-2, -1, -1, -1])
        return sb

    def _clear_value_text(self):
        self._current_text.SetLabel("")
        self._value_hex.SetLabel("")
        self._value_dec.SetLabel("")
        self._value_bin.SetLabel("")
        self._value_chr.SetLabel(" ")

    def _set_value_text(self, value):
        self._value_hex.SetLabel(hex(value).replace("0x", "").upper().zfill(2))
        self._value_dec.SetLabel(str(value))
        self._value_bin.SetLabel(bin(value).replace("0b", "").zfill(8))

        if 0x20 <= value <= 0x7E:
            self._value_chr.SetLabel(chr(value) + " ")
        else:
            self._value_chr.SetLabel(" ")

    def _update_status(self, length=None, row=None, col=None, sel=None):
        if length is not None:
            self.status_bar.SetStatusText("Length: 0x%X(%d)" % (length, length), 0)
        if row is not None:
            self.status_bar.SetStatusText("Row: %s" % row, 1)
        if col is not None:
            self.status_bar.SetStatusText("Col: %s" % col, 2)
        if sel is not None:
            self.status_bar.SetStatusText("Selected: %s" % sel, 3)

    @property
    def HexCols(self):
        return self._hex_cols

    def GetBinary(self):
        return self.grid.GetTable().String

    def SetBinary(self, binary):
        self.SetBinary(binary)

    Binary = property(GetBinary, SetBinary, doc="Set/Get Binary String")

    @property
    def Length(self):
        return self.grid.GetTable().length

    def _set_grid_table(self, table):
        self.grid.BeginBatch()
        self._reset_grid()
        self.grid.SetTable(table, True)
        self.AutoSize()
        self.grid.EndBatch()

        self._update_status(length=table.length)
        self.toolbar.DoLayout()

    def GetCurrentAddr(self):
        row, col = self.grid.GridCursorRow, self.grid.GridCursorCol
        addr = row * self.HexCols + col
        return addr

    def SetCurrentAddr(self, addr):
        if addr < self.Length:
            row, col = self.AddrToRowCol(addr)
            self.grid.SetGridCursor(row, col)
            self.SetSelection(addr, 1, False)
            self.JumpTo(row, col)
            self.grid.SetFocus()

    CurrentAddr = property(GetCurrentAddr, SetCurrentAddr, doc="Set/Get Current Address")

    def GetCurrentRowCol(self):
        return self.grid.GridCursorRow, self.grid.GridCursorCol

    def SetCurrentRowCol(self, position):
        row, col = position
        self.grid.SetGridCursor(row, col)

    CurrentRowCol = property(GetCurrentRowCol, SetCurrentRowCol, doc="Set/Get Current Row and Col")

    @property
    def Selection(self):
        cells = self.grid.GetSelectedCells()
        top_left = self.grid.GetSelectionBlockTopLeft()
        bottom_right = self.grid.GetSelectionBlockBottomRight()

        addrs = [self.RowColToAddr(row, col) for (row, col) in top_left + bottom_right + cells]
        if addrs:
            min_addr = min(addrs)
            max_addr = max(addrs)
            return min_addr, max_addr - min_addr + 1

    def SetBinary(self, binary, length=None):
        """
        bytes string
        """
        if not isinstance(binary, str) and not isinstance(binary, bytes):
            raise Exception("binary must be string")

        table = HexGridTable(binary, length)
        self._set_grid_table(table)

    def SetBinaryFile(self, path, length=-1):
        """ filename
        """
        bin_file = open(path, "rb")
        binary = bin_file.read(length)
        bin_file.close()
        self.SetBinary(binary, length=length)

    def _file_dialog(self, *args, **kwargs):
        wildcard = 'Binary files (*.bin;*.txt)|*.bin;*.txt|All files (*.*)|*.*'
        kwargs.update({
            "wildcard": wildcard
        })
        dlg = wx.FileDialog(self, *args, **kwargs)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            dlg.Destroy()
            return filename
        dlg.Destroy()

    def MessageBox(self, message, title="", style=wx.OK | wx.ICON_INFORMATION):
        dlg = gmd.GenericMessageDialog(self, message, title, style)
        res = dlg.ShowModal()
        dlg.Destroy()
        return res

    def NewDialog(self):
        dlg = wx.TextEntryDialog(self, "Size in bytes", "New Binary", str(256))
        res = dlg.ShowModal()
        dlg.Destroy()
        if res == wx.ID_OK:
            size = dlg.GetValue()
            size = int(size)
            self.Binary = '\x00' * size
            self.grid.SetFocus()

    def OpenFileDialog(self):
        filename = self._file_dialog("Load a file", style=wx.FD_OPEN)
        if filename:
            self.LoadFile(filename)

    def SaveFileDialog(self):
        filename = self._file_dialog("Save to file", style=wx.FD_SAVE, defaultFile="backup.bin")
        if filename:
            if os.path.isfile(filename):
                res = self.MessageBox("A file with the name '%s' already exists, "
                                      "do you want to replace it?" % os.path.basename(filename),
                                      "File Replace", wx.YES_NO | wx.ICON_WARNING)
                if res == wx.ID_NO:
                    return
            self.SaveFile(filename)

    def LoadFile(self, filename):
        if os.path.isfile(filename):
            self.SetBinaryFile(filename, os.path.getsize(filename))
        else:
            self.MessageBox("Can not open file %s" % filename, "Load File Error", wx.OK | wx.ICON_ERROR)
        self.grid.SetFocus()

    def SaveFile(self, filename):
        f = open(filename, "wb")
        self.grid.GetTable().SaveFile(f)
        f.close()

    def GetCellString(self, row, col, length=1):
        val = ""
        if row < self.grid.GetNumberRows() and col < self.HexCols:
            val = self.grid.GetCellValue(row, col)
        return val

    def SetCellString(self, row, col, val):
        """ val must be Hex string
        """
        val = int(val, 16)
        # update the table
        addr = self.RowColToAddr(row, col)

        self.grid.SetCellValue(row, col, "%02X" % val)

    def AddrToRowCol(self, addr):
        return addr / self.HexCols, addr % self.HexCols

    def RowColToAddr(self, row, col, check_max=True):
        col = self.HexCols - 1 if col >= self.HexCols else col
        addr = row * self.HexCols + col
        if check_max:
            addr = self._check_addr_in_range(addr)
        return addr

    def SetSelection(self, addr, length=1, jumpto=False):
        row, col = self.AddrToRowCol(addr)
        end_row, end_col = self.AddrToRowCol(addr + length - 1)

        self.grid.Freeze()
        self.grid.BeginBatch()
        self.grid.SetGridCursor(row, col)
        if length > 0:
            # in same row
            if row == end_row:
                self.grid.SelectBlock(row, col, end_row, end_col)
            elif end_row > row:
                #first row
                self.grid.SelectBlock(row, col, row, self.HexCols - 1)
                if end_row - row > 1:
                    self.grid.SelectBlock(row + 1, 0, end_row - 1, self.HexCols - 1, addToSelected=True)
                #last row
                self.grid.SelectBlock(end_row, 0, end_row, end_col, addToSelected=True)
        self.grid.EndBatch()
        self.grid.Thaw()
        self._update_status(sel=length)
        if jumpto:
            self.JumpTo(row, col)

    def GetSelection(self):
        return self.Selection

    def OnMenuButton(self, event):
        self.PopupMenu(self.menu)
        event.Skip()

    def OnTransmissionButton(self, event):
      print("OnTransmissionButton")
      
      dlg = wx.MessageDialog(parent = None, message = u"終了します。よろしいですか？", caption = u"終了確認", style = wx.YES_NO)
      result = dlg.ShowModal()
      if result == wx.ID_YES:
        table = self.grid.GetTable()
        buf = table.GetBuffer()
        with open("log/data.bin", "wb") as fout:        
            for x in buf:
                fout.write(x)
        wx.Exit()

    def OnFindButton(self, event):
        event.Skip()
        text = self._find_text.GetValue()

        if not text:
            self._search_result = None
            return

        options = {
            "text": text,
            "search_type": "",
        }

        for radio in self.find_types:
            if radio.GetValue() is True:
                options["search_type"] = radio.GetLabel()

        if self._search_options.get("text") != options["text"] or\
            self._search_options.get("search_type") != options["search_type"] or\
                self._search_result is None:

                    if options["search_type"] == SEARCH_TYPES.Hexadecimal:
                        text = re.sub(r'\s+', '', text)

                    try:
                        self._search_result = self.grid.GetTable().FindIter(text, options["search_type"])
                        self._search_options = options
                    except Exception as e:
                        self.MessageBox("Error: %s" % str(e), "Search Error", wx.OK | wx.ICON_ERROR)
                        return

        try:
            match = self._search_result.__next__()
            start, end = match.span(0)
            self.SetSelection(start, end - start, True)
            self.grid.SetFocus()
        except StopIteration as e:
            self._search_result = None  # restart
            self.MessageBox("Search to End", "Search Done")
        except Exception as e:
            self.MessageBox("Error: %s" % str(e), "Search Error", wx.OK | wx.ICON_ERROR)

    def OnFindKeyDown(self, event):
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.OnFindButton(event)
            self._find_text.SetFocus()
            return
        event.Skip()

    # セルの選択時
    def OnSelectCell(self, event):
        row = event.GetRow()
        col = event.GetCol()

        addr = self.RowColToAddr(row, col)

        value = self.GetCellString(row, col)
        self._clear_value_text()
        if value:
            value = int(value, 16)
            self._set_value_text(value)
            self._current_text.SetLabel("%X" % addr)

        self._update_status(row=row, col=col)
        event.Skip()

    def OnCellRightClicked(self, event):
        self.grid.PopupMenu(self._grid_menu)
        event.Skip()

    def OnCellChanged(self, signal, grid, row, col, val):
        if grid == self.grid:
            self.SetCellString(row, col, val)
            dispatcher.send("HexEditor.Changed", sender=self, row=row, col=col, val=val)

    def OnCurrentKeyDown(self, event):
        event.Skip()
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            addr = int(self._current_text.GetValue(), 16)
            self.CurrentAddr = addr

    def OnGridKeyDown(self, event):
        key = event.GetKeyCode()
        controlDown = event.ControlDown()
        altDown = event.AltDown()
        if controlDown and altDown:
            event.Skip()

        if controlDown and key in (ord('A'), ord('a')):
            self.SetSelection(0, self.Length, False)
        
        elif controlDown and key in (ord('Z'), ord('z')):
            self.Undo()
        
        elif controlDown and key in (ord('Y'), ord('y')):
            self.Redo()
        
        elif controlDown and key in (ord('C'), ord('c')):
            self._copy()
        
        elif controlDown and key in (ord('X'), ord('x')):
            self._cut()
        
        elif controlDown and key in (ord('V'), ord('v')):
            self._paste()
        
        elif controlDown and key in (ord('S'), ord('s')):
            self.SaveFileDialog()
        
        elif controlDown and key in (ord('O'), ord('o'), ord('L'), ord('l')):
            self.OpenFileDialog()
        
        elif controlDown and key in (ord('N'), ord('n')):
            self.NewDialog()

        elif controlDown and key in (ord('F'), ord('f')):
            selection = self.Selection
            if selection:
                start, length = selection
                value = self.grid.GetTable().GetText(start, length)
                self._find_text.SetValue(value)
                self._find_text.SetFocus()
                self._find_text.SelectAll()
        
        elif key in (wx.WXK_F3,):
            self.OnFindButton(event)
            self.grid.SetFocus()
        
        elif key in (wx.WXK_DELETE,):
            self._delete()
        
        elif key in (wx.WXK_INSERT,):
            self._insert()
        
        elif key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_TAB):
            row, col = self.CurrentRowCol
            if col >= self.HexCols - 1:
                self.CurrentRowCol = (row + 1, 0)
            else:
                event.m_keyCode = wx.WXK_TAB
                event.Skip()
        else:
            event.Skip()

    def _check_addr_in_range(self, addr):
        addr = addr if addr > 0 else 0
        addr = addr if addr < self.Length else self.Length - 1
        return addr

    def _set_selection(self, end_pos=None, callback=None):
        self._in_selecting = True
        if end_pos and self._grid_selecting_start:
            cur_row, cur_col = self._grid_selecting_start
            end_row, end_col = end_pos

            if cur_col == self.HexCols:
                if cur_row > end_row:
                    cur_row, end_row = end_row, cur_row
                min_addr = self.RowColToAddr(cur_row, 0)
                max_addr = self.RowColToAddr(end_row, self.HexCols - 1)
                self.SetSelection(min_addr, max_addr - min_addr + 1, False)
            else:
                if end_col == self.HexCols:
                    end_col -= 1
                if (cur_row, cur_col) == (end_row, end_col):
                    min_addr = max_addr = self.RowColToAddr(cur_row, cur_col, False)
                    if min_addr > self.Length:
                        min_addr = max_addr = self.Length
                else:
                    min_addr = self.RowColToAddr(cur_row, cur_col)
                    max_addr = self.RowColToAddr(end_row, end_col)
                    if min_addr > max_addr:
                        min_addr, max_addr = max_addr, min_addr

                self.SetSelection(min_addr, max_addr - min_addr + 1, False)
        else:
            rows = self.grid.GetSelectedRows()
            if rows:
                min_row = min(rows)
                max_row = max(rows)
                self.grid.SetGridCursor(min_row, 0)
                self.grid.ClearSelection()
                min_addr = self.RowColToAddr(min_row, 0)
                max_addr = self.RowColToAddr(max_row, self.HexCols - 1)
                self.SetSelection(min_addr, max_addr - min_addr + 1, False)
            else:
                top_left = self.grid.GetSelectionBlockTopLeft()
                bottom_right = self.grid.GetSelectionBlockBottomRight()
                cells = self.grid.GetSelectedCells()

                result = []
                result.append(top_left)
                result.append(bottom_right)
                result.append(cells)
                addrs = []
                #addrs = [self.RowColToAddr(row, col) for (row, col) in top_left + bottom_right + cells]
                #addrs = [self.RowColToAddr(row, col) for (row, col) in result]
                
                if addrs:
                    min_addr = min(addrs)
                    max_addr = max(addrs)
                    self.SetSelection(min_addr, max_addr - min_addr + 1, False)
                else:
                    self._update_status(sel=1)

        self._in_selecting = False
        if callable(callback):
            callback()
        #self.grid.Refresh()

    def _reset_grid_selecting(self):
        self._grid_selecting_start = None

    def _client_to_scroll_pos(self, x, y):
        ppunit = self.grid.GetScrollPixelsPerUnit()
        scroll_x = self.grid.GetScrollPos(wx.HORIZONTAL)
        scroll_y = self.grid.GetScrollPos(wx.VERTICAL)
        x += scroll_x * ppunit[0]
        y += scroll_y * ppunit[1]
        return x, y

    def OnGridColLeftDown(self, event):
        # disable col selection
        pass

    def OnGridLeftDown(self, event):
        start_pos = self._client_to_scroll_pos(event.X, event.Y)
        self._grid_selecting_start = self.grid.XYToCell(*start_pos)
        event.Skip()

    def OnGridLeftUp(self, event):
        event.Skip()
        wx.CallAfter(self._set_selection, callback=self._reset_grid_selecting)

    def OnGridLeftMotion(self, event):
        if not self._in_selecting and self._grid_selecting_start:
            end_pos = self._client_to_scroll_pos(event.X, event.Y)
            end_pos = self.grid.XYToCell(*end_pos)
            if end_pos != (-1, -1):
                wx.CallAfter(self._set_selection, end_pos=end_pos)

    def OnGridRowLeftUp(self, event):
        event.Skip()
        wx.CallAfter(self._set_selection, callback=self._reset_grid_selecting)

    def OnValueTextChar(self, event):
        key = event.GetKeyCode()
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            text_ctrl = event.EventObject
            val = text_ctrl.GetValue()
            if val and val.strip():
                if text_ctrl == self._value_hex:
                    val = int(val, 16)
                elif text_ctrl == self._value_dec:
                    val = int(val, 10)
                    if val > 0xFF:
                        return
                elif text_ctrl == self._value_bin:
                    val = int(val, 2)
                else:
                    raise Exception("unknown text ctrl")

                self._set_value_text(val)
                row, col = self.CurrentRowCol
                self.SetCellString(row, col, hex(val))

            text_ctrl.SetInsertionPointEnd()
            text_ctrl.SetSelection(0, -1)

        event.Skip()

    def JumpTo(self, row, col):
        ppunit = self.grid.GetScrollPixelsPerUnit()
        cell_coords = self.grid.CellToRect(row, col)
        y = cell_coords.y / ppunit[1]  # convert pixels to scroll units
        scrollPageSize = self.grid.GetScrollPageSize(wx.VERTICAL)
        scroll_coords = (0, y - scrollPageSize / 2)
        self.grid.Scroll(*scroll_coords)

    def _get_data_from_clipboard(self):
        data = wx.TextDataObject()
        wx.TheClipboard.Open()
        success = wx.TheClipboard.GetData(data)
        wx.TheClipboard.Close()
        return data.GetText() if success else None

    def _cut(self):
        self._copy()
        self._delete()

    def _copy(self):
        selection = self.Selection
        if selection:
            start, length = selection
            self.SetSelection(start, length)
        else:
            start = self.CurrentAddr
            length = 1

        binary = self.grid.GetTable().GetText(start, length)
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(wx.TextDataObject(binary))
        wx.TheClipboard.Close()

    def _paste(self):
        self._delete(False)
        self._insert()

    def _delete(self, delete_cell=True):
        selection = self.Selection
        if selection:
            start, length = selection
            self.SetSelection(start, length)
        else:
            if not delete_cell:
                return
            start = self.CurrentAddr
            length = 1

        table = self.grid.GetTable()
        table.DeleteRange(start, length)
        self._set_grid_table(table)

    def _insert(self):
        data = self._get_data_from_clipboard()
        if data:
            start = self.CurrentAddr

            table = self.grid.GetTable()
            data = re.sub("[\n\r]\S{8} ", "", data)
            data = re.sub(r'\s+', '', data)
            if data:
                if len(data) % 2:
                    data = data[:-1]
                try:
                    table.InsertText(start, data)
                    self._set_grid_table(table)
                except Exception as e:
                    self.MessageBox(str(e), "Insert Data Error", wx.OK | wx.ICON_ERROR)

    def Undo(self):
        table = self.grid.GetTable()
        res = table.Undo()
        if res is True:
            self._set_grid_table(table)
        elif res is False:
            self.Refresh()

    def Redo(self):
        table = self.grid.GetTable()
        res = table.Redo()
        if res is True:
            self._set_grid_table(table)
        elif res is False:
            self.Refresh()