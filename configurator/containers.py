class DictList(object):
    """
    DictList allows one to set a global option in advance, providing data 
    from one module to another, not having to deal with applications 
    order in INSTALLED_APPS.
    
    Can be used as an ordered set:
    >>> KEY = DictList()

    >>> KEY += 'xxx'
    >>> KEY
    ['xxx']
    >>> KEY += 'yyy'
    >>> KEY 
    ['xxx', 'yyy']
    >>> KEY -= 'xxx'
    >>> KEY
    ['yyy']
    
    In Django, this can be used for AUTHENTICATION_BACKENDS,
    TEMPLATE_CONTEXT_PROCESSORS, MIDDLEWARE_CLASSES, ADMINS,
    LANGUAGES and other settings.
    
    Or as an ordered dict:

    >>> D = DictList()
    >>> D['abc'] = 'def'
    >>> D['key'] = 'value'
    >>> D.default = '(default)'
    >>> D
    {default=(default), 'abc': 'def', 'key': 'value'}

    In Django, this can be used for DATABASES setup, and, i hope,
    in Django 1.3, for LOGGING setup and APP_MEDIA setup.
    """
    
    def __init__(self, keys=None, values=None):
        self._type = None
        if keys is None:
            self._keys = []
        else:
            self._keys = keys
        self._values = {}
        if values is not None:
            self._keys = values.keys()
            self._values = dict(values)
        self._default = None

    def set_type(self, type):
        if self._type is None:
            self._type = type
        elif self._type != type:
            raise TypeError("Switching type is not allowed (from %s to %s)" % 
                            (self._type, type))

    def __iadd__(self, key):
        self.set_type('list')
        if not key in self._keys:
            self._keys.append(key)
        return self

    def __len__(self):
        return len(self._keys)

    def __isub__(self, key):
        self.set_type('list')
        if key in self._keys:
            self._keys.remove(key)
        return self

    def __unicode__(self):
        if self._type == 'dict':
            r = []
            if self._default is not None:
                r.append("default=%s" % self._default)
            for k in self._keys:
                r.append("%r: %r" % (k, self._values[k]))
            return "{%s}" % ", ".join(r)
        elif self._type == 'list':
            return repr(self._keys)
        else:
            return "()"

    def __str__(self):
        return unicode(self).encode('utf-8', 'replace')

    def __repr__(self):
        return unicode(self)

    def __contains__(self, key):
        return key in self._keys

    def __setitem__(self, key, value):
        self.set_type('dict')
        if not key in self._keys:
            self._keys.append(key)
        self._values[key] = value

    def __getitem__(self, key):
        try:
            return self._values[key]
        except KeyError:
            return self._default

    def __iter__(self):
        for k in self._keys:
            yield k
            
    def keys(self):
        return self._keys
    
    def items(self):
        return self._values.items()
    
    def iterkeys(self):
        return self._keys.__iter__()
            
    def iteritems(self):
        return self._values.iteritems()

    def empty(self):
        return self._type is None

    def __get__(self, obj, objtype=None):
        print "ListDict.__get__"

    def __set__(self, obj, value):
        print "ListDict.__set__"

    def get_default(self):
        return self._default
    
    def set_default(self, value):
        self.set_type('dict')
        self._default = value

    default = property(get_default, set_default)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
