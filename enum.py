# -*- coding: utf-8 -*-

class Enum(object):
    """ support class for enum
    """
    __names__ = None
    __items__ = None
    __special_names__ = []

    @classmethod
    def Name(cls, val):
        if cls.__names__ is None:
            cls.__names__ = dict([(getattr(cls, name), name) for name in dir(cls)
                                  if name and not name.startswith("_") and name not in cls.__special_names__ and
                                  not callable(getattr(cls, name))])

        return cls.__names__.get(val, val)

    @classmethod
    def Names(cls):
        return [name for name in dir(cls)
                if name and not name.startswith("_") and name not in cls.__special_names__ and
                not callable(getattr(cls, name))]

    @classmethod
    def Value(cls, name):
        items = cls.Items()
        if name not in items:
            raise AttributeError("No item '%s" % name)
        return items[name]

    @classmethod
    def Values(cls):
        return [getattr(cls, name) for name in dir(cls)
                if name and not name.startswith("_") and name not in cls.__special_names__ and
                not callable(getattr(cls, name))]

    @classmethod
    def Items(cls):
        if cls.__items__ is None:
            cls.__items__ = dict([(name, getattr(cls, name)) for name in dir(cls)
              if name and not name.startswith("_") and name not in cls.__special_names__ and
                not callable(getattr(cls, name))])
        return cls.__items__