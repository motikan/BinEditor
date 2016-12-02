#!/usr/bin/env python
# -*- coding: utf-8 -*-
import wx
import ctypes
import wx.grid as wxgrid
import struct
from enum import Enum
from wx.py import dispatcher
from search_types import SEARCH_TYPES

class HexGridTable(wx.grid.PyGridTableBase):
    class Actions:
        EditCell = "EditCell"
        RemoveCells = "RemoveCells"
        InsertCells = "InsertCells"

    def __init__(self, binary, length=None, hex_cols=16):
        #wx.grid.PyGridTableBase.__init__(self)
        wx.grid.GridTableBase.__init__(self)

        if length is None:
            self.length = len(binary)
        else:
            self.length = length
        if self.length < 0:
            self.length = 0

        self.hex_cols = hex_cols
        self.cols_labels = ["%X" % i for i in range(self.hex_cols)] + ["        Dump       "]

        self.buffer = ctypes.create_string_buffer(self.length)
        ctypes.memmove(self.buffer, binary, self.length)

        self._string = None

        self._dump_cell_attr = wxgrid.GridCellAttr()
        self._dump_cell_attr.SetReadOnly(True)
        self._dump_cell_attr.SetAlignment(wx.ALIGN_LEFT, wx.ALIGN_CENTER)

        self._alt_cell_attr = wxgrid.GridCellAttr()
        self._alt_cell_attr.SetBackgroundColour("#DDDDDD")
        self._page_row_attr = wxgrid.GridCellAttr()
        self._page_row_attr.SetBackgroundColour("#CCFDFD")
        self._range_attr = wxgrid.GridCellAttr()
        self._range_attr.SetBackgroundColour("#F2F5A9")
        self._changed_cell_attr = wxgrid.GridCellAttr()
        self._changed_cell_attr.SetBackgroundColour("#F2F5A9")
        self._changed_cell_attr.SetTextColour("red")

        self._changed_attr = {}

        self._changed_range = (-1, -1)
        self._undo_list = []
        self._redo_list = []

    @property
    def String(self):
        if self._string is None:
            self._string = ctypes.string_at(self.buffer, self.length)
        return self._string

    def _get_value_by_row_col(self, row, col, length=1):
        addr = row * self.hex_cols + col
        return self._get_value_by_addr(addr, length)

    def _get_value_by_addr(self, addr, length=1):
        end = addr + length
        if addr + length > self.length:
            end = self.length
        return self.buffer[addr:end]

    def _set_value_by_addr(self, addr, value):
        if addr > self.length:
            return False
        if addr == self.length:  # append one byte
            self.InsertRange(self.length, value)
        else:  # change one byte
            self.buffer[addr] = value
        self._string = None  # reset string
        return True

    def addr_to_row_col(self, addr):
        return addr / self.hex_cols, addr % self.hex_cols

    def row_col_to_addr(self, row, col):
        return row * self.hex_cols + col

    def _in_changed_range(self, addr):
        return self._changed_range[0] <= addr < self._changed_range[1]

    def Reset_Attr(self):
        self._changed_attr = {}

    def GetNumberCols(self):
        return self.hex_cols + 1

    def GetNumberRows(self):
        return (self.length + self.hex_cols) / self.hex_cols

    def GetColLabelValue(self, col):
        return self.cols_labels[col]

    def GetRowLabelValue(self, row):
        return "0x%X " % (row * self.hex_cols)

    def IsEmptyCell(self, row, col):
        addr = row * self.hex_cols + col
        if addr >= self.length:
            return True
        return False

    def GetAttr(self, row, col, kind=None):
        if col == self.hex_cols:  # disable cell editor for Dump col
            self._dump_cell_attr.IncRef()
            return self._dump_cell_attr
        addr = row * self.hex_cols + col

        if addr > self.length:  # disable cell editor for cells > length
            self._dump_cell_attr.IncRef()
            return self._dump_cell_attr

        if addr in self._changed_attr:  # return changed cells attr first
            attr = self._changed_attr[addr]
            if attr:
                attr.IncRef()
            return attr
        elif self._in_changed_range(addr):  # return range change attr
            self._range_attr.IncRef()
            return self._range_attr
        elif row and not (row % 0x20):   # return pager attr
            self._page_row_attr.IncRef()
            return self._page_row_attr
        elif col in [4, 5, 6, 7, 12, 13, 14, 15]:   # return range change attr
            self._alt_cell_attr.IncRef()
            return self._alt_cell_attr

        # return None for others

    def SetAttr(self, attr, row, col):
        addr = row * self.hex_cols + col
        if addr in self._changed_attr:   # decrease ref for saved attr
            old_attr = self._changed_attr[addr]
            if old_attr:
                old_attr.DecRef()
        self._changed_attr[addr] = attr  # save changed cell attr

    def GetValue(self, row, col):
        if col == self.hex_cols:  # dump col
            row_values = self._get_value_by_row_col(row, 0, 16)
            #row_values = ["%c" % val if 0x20 <= ord(val) <= 0x7E else "." for val in row_values if val]
            row_values = ["%c" % val if 0x20 <= val <= 0x7E else "." for val in row_values if val]
            
            return "  " + "".join(row_values)
        else:
            val = self._get_value_by_row_col(row, col, 1)
            return val and "%02X" % ord(val)

    def SetValue(self, row, col, value):
        if col == self.hex_cols:
            pass
        else:
            addr = row * self.hex_cols + col
            value = struct.pack('B', int(value, 16))
            #value = chr(int("6c", 16))

            attr = self.GetAttr(row, col)
            saved_val = self._get_value_by_addr(addr)

            in_range = addr < self.length  # add undo for addr < length

            if saved_val != value and self._set_value_by_addr(addr, value):
                self._changed_cell_attr.IncRef()
                self.SetAttr(self._changed_cell_attr, row, col)
                if in_range:
                    self._add_undo_action(self.Actions.EditCell, (addr, saved_val, attr))
                else:
                    if col == self.hex_cols - 1:
                        # this is the last row/col, append a row
                        msg = wxgrid.GridTableMessage(self,
                                wxgrid.GRIDTABLE_NOTIFY_ROWS_APPENDED,
                                1)
                        self.GetView().ProcessTableMessage(msg)

    def SaveFile(self, output):
        """ output must be a file like object supports 'write' """
        output.write(ctypes.string_at(self.buffer, self.length))

    def GetBinary(self, start=0, length=None):
        if length is None:
            length = self.length
        if start + length > self.length:
            length = self.length - length
        return ctypes.string_at(ctypes.addressof(self.buffer) + start, length)

    def GetText(self, start=0, length=None):
        return binascii.b2a_hex(self.GetBinary(start, length)).upper()

    def InsertText(self, start, text):
        value = binascii.a2b_hex(text)
        self.InsertRange(start, value)

    def _delete_range(self, start, length):
        if start >= self.length:
            return ""
        self._changed_range = (-1, -1)

        deleted_data = ctypes.create_string_buffer(length)
        buf_addr = ctypes.addressof(self.buffer)
        if start + length > self.length:
            length = self.length - length
            ctypes.memmove(deleted_data, buf_addr + start, length)
            self.length -= length
        else:
            ctypes.memmove(deleted_data, buf_addr + start, length)
            ctypes.memmove(buf_addr + start, buf_addr + start + length, self.length - length - start)
            self.length -= length
            self.Reset_Attr()

        self._string = None  # reset string

        dispatcher.send("HexEditor.Changed", sender=self.GetView())

        return deleted_data

    def DeleteRange(self, start, length):
        deleted_data = self._delete_range(start, length)

        self._add_undo_action(self.Actions.RemoveCells, (start, length, deleted_data))

    def _insert_range(self, start, value):
        if start >= self.length:
            start = self.length

        length = len(value)
        new_buf = ctypes.create_string_buffer(self.length + length)
        new_buf_addr = ctypes.addressof(new_buf)

        old_addr = ctypes.addressof(self.buffer)

        self._changed_range = (start, start + length)

        ctypes.memmove(new_buf_addr, old_addr, start)  # copy range before insert point
        ctypes.memmove(new_buf_addr + start, value, length)  # copy insertion value
        # copy range after insert point
        ctypes.memmove(new_buf_addr + start + length, old_addr + start, self.length - start)

        self.buffer = new_buf
        self.length += length

        self.Reset_Attr()

        self._string = None  # reset string

        dispatcher.send("HexEditor.Changed", sender=self.GetView())

        return start

    def InsertRange(self, start, value):
        start = self._insert_range(start, value)

        self._add_undo_action(self.Actions.InsertCells, (start, value))

    def _add_undo_action(self, action, data):
        self._undo_list.append((action, data))
        if action == self.Actions.EditCell:
            return False
        return True

    def _add_redo_action(self, action, data):
        self._redo_list.append((action, data))
        if action == self.Actions.EditCell:
            return False
        return True

    def Undo(self):
        try:
            item = self._undo_list.pop()
            action, data = item
            action, data = self.Do(action, data)
            if action is False:
                return self._add_undo_action(*item)
            elif action is not None:
                return self._add_redo_action(action, data)
        except IndexError:
            return

    def Redo(self):
        try:
            item = self._redo_list.pop()
            action, data = item
            action, data = self.Do(action, data)
            if action is False:
                return self._add_redo_action(*item)
            if action is not None:
                return self._add_undo_action(action, data)
        except IndexError:
            return

    def Do(self, action, data):
        if action == self.Actions.EditCell:
            addr, value, attr = data
            row, col = self.addr_to_row_col(addr)
            saved_value = self._get_value_by_addr(addr)
            saved_attr = self.GetAttr(row, col)
            if self._set_value_by_addr(addr, value):
                self.SetAttr(attr, row, col)
                return  self.Actions.EditCell, (addr, saved_value, saved_attr)
            return False, False

        elif action == self.Actions.RemoveCells:
            start, length, deleted_data = data
            try:
                start = self._insert_range(start, deleted_data)
                return self.Actions.InsertCells, (start, deleted_data)
            except:
                return False, False

        elif action == self.Actions.InsertCells:
            start, deleted_data = data
            try:
                deleted_data = self._delete_range(start, len(deleted_data))
                return self.Actions.RemoveCells, (start, len(deleted_data), deleted_data)
            except:
                return False, False

        return None, None

    def FindIter(self, text, find_type=SEARCH_TYPES.Hexadecimal):
        """ return a iter """
        if find_type == SEARCH_TYPES.RegexText:
            regex = text
        elif find_type == SEARCH_TYPES.Hexadecimal:
            text = binascii.a2b_hex(text)
            regex = re.escape(text)
        elif find_type == SEARCH_TYPES.NormalText:
            regex = re.escape(text)
        else:
            raise Exception("unsupported search type")

        return self.FindRegex(regex)

    def FindRegex(self, regex):
        return re.finditer(regex, self.String)

    def test(self):
        return self.buffer
