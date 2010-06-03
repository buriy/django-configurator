from collections import defaultdict
from discovery import site_name, ListFiles
from traceback import print_exc
import os.path
import types
from django.utils.importlib import _resolve_name
import imp

class AppList(dict):
    def __init__(self):
        super(AppList, self).__init__()

    def default(self, key):
        self[key] = Config(key)
        return self[key]
    
    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return self.default(key)

    def get(self, key, *args):
        if not args:
            args = (self.default(key),)
        return dict.get(self, key, *args)

class DictList(object):
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

    def __isub__(self, key):
        self.set_type('list')
        if key in self._keys:
            self._keys.remove(key)
        return self

    def __unicode__(self):
        if self._type == 'dict':
            r = []
            for k in self._keys:
                r += ["%s => %s" % (k, self._values[k])]
            return "\n".join(r)
        elif self._type == 'list':
            return repr(self._keys)
        else:
            return "{}"

    def __str__(self):
        return unicode(self).encode('utf-8', 'replace')

    def __repr__(self):
        return unicode(self)

    def __contains__(self, key):
        return key in self._keys

    def __setitem__(self, key, value):
        if _DEBUG >= 2: 
            print "Setting [ key =", key, '] to value =', value
        if not key in self._keys:
            self._keys.append(key)
        self._values[key] = value

    def __getitem__(self, key):
        if _DEBUG >= 2: print "Getting value at [", key, ']'
        try:
            if _DEBUG >= 2: print '->', self._values[key]
            return self._values[key]
        except KeyError:
            if _DEBUG >= 2: print '->', self._default
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


class LazyGetter(object):
    def __init__(self, target):
        self.target = target
    
    def __getattr__(self, name):
        if _DEBUG >= 3:
            print 'lazy get key =', name

        target = self.target

        class lazy(object):
            def __call__(self):
                return getattr(target, name)

            def __repr__(self):
                return "<%r::%s>" % (target, name)

        return lazy()


class Config(object):
    def __init__(self, app_name=None):
        self._app_name = app_name
        
    def __iter__(self):
        for k in self.__dict__:
            yield k
            
    def keys(self):
        return self.__dict__.keys()
    
    def items(self):
        return self.__dict__.items()
    
    def iterkeys(self):
        for k in self.__dict__:
            yield k
            
    def iteritems(self):
        for k, v in self.__dict__.iteritems():
            yield k, v

    def __getattr__(self, key):
        if key == '_app_name':
            print '_app_name', key
        try:
            return object.__getattribute__(self, key)
        except AttributeError:
            setattr(self, key, DictList())
            return getattr(self, key)

    def __unicode__(self):
        r = []
        for k, v in self.__dict__.iteritems():
            r += ["%s => %s" % (k, repr(v))]
        return "\n".join(r)

    def __str__(self):
        return unicode(self).encode('utf-8', 'replace')

    def __repr__(self):
        if self._app_name is None:
            return "<Settings>"
        return "<AppSettings: %s>" % (self._app_name)

    @property
    def lazy(self):
        return LazyGetter(self)

_DEBUG = 0

def set_debug_level(level):
    global _DEBUG
    old_level, _DEBUG = level
    return old_level

options = Config()
options.apps = AppList()

options.CONF = 'conf'
options.APP_CONF = 'conf.apps'
options.ROOT = os.path.dirname(os.path.abspath(__name__))
options.SITE = site_name()

options.DISCOVERY_ORDER = [
    ListFiles('django.conf', 'global'), # django/conf/global.py
    ListFiles(options.lazy.CONF, 'global'),# conf/global.py
    ListFiles(options.lazy.CONF, options.lazy.SITE), # conf/<site>.py
    ListFiles(options.lazy.INSTALLED_APPS, 'conf'), # app1/conf.py
    ListFiles(options.lazy.APP_CONF, options.lazy.INSTALLED_APPS), # conf/app1.py
    ListFiles(options.lazy.CONF, 'global', '_overrides'), # conf/global_overrides.py
    ListFiles(options.lazy.CONF, options.lazy.SITE, '_overrides'), # conf/<site>_overrides.py
]

def update_options(source, destination):
    for k, v in source.iteritems():
        if isinstance(k, types.ModuleType):
            continue
        if k is options:
            continue
        if not k.upper() == k:
            continue
        if k.startswith('_'):
            continue
        if isinstance(k, (types.ListType, types.TupleType)):
            k = DictList(keys = k)
        if _DEBUG >= 3: 
            print 'set', k, '=', v
        setattr(destination, k, v)

def autodiscover(locals=None):
    from django.utils.importlib import import_module
    if locals is not None:
        update_options(locals, options)
    
    for files in options.DISCOVERY_ORDER:
        for path, name in files:
            if path.startswith('django.'):
                continue
            try:
                mod = path+ '.' + name.replace('.', '__') 
                if _DEBUG == 1:
                    print 'importing', mod
                if _DEBUG >= 2:
                    print 'loading', mod
                import_module(mod)
                if _DEBUG >= 3:
                    print 'Ok'
            except ImportError, e:
                last = mod.split('.')[-1]
                last2 = '.'.join(mod.split('.')[-2:])
                if str(e) != 'No module named %s' % last and \
                    str(e) != 'No module named %s' % last2:
                    print "Can't import %s:" % mod
                    print_exc()
            except Exception:
                print_exc()

    if locals is not None:
        for opt, value in options.iteritems():
            if opt.upper() == opt:
                if _DEBUG >= 3:
                    print 'Updating settings key', opt
                locals[opt] = value
