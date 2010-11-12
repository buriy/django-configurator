from configurator.containers import DictList
from discovery import site_name, ListFiles
from traceback import print_exc
import imp
import os.path
import types

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
    old_level, _DEBUG = _DEBUG, level
    return old_level

options = Config()
options.apps = AppList()

options.CONF = 'conf'
options.APP_CONF = 'conf.apps'
options.ROOT = os.path.dirname(os.path.abspath(__name__))
options.SITE = site_name()

options.DISCOVERY_ORDER = [
    ListFiles(options.lazy.CONF, 'global'),# conf/global.py
    ListFiles(options.lazy.CONF, options.lazy.SITE), # conf/<site>.py
    ListFiles(options.lazy.INSTALLED_APPS, 'conf'), # app1/conf.py
    ListFiles(options.lazy.APP_CONF, options.lazy.INSTALLED_APPS), # conf/app1.py
    ListFiles(options.lazy.CONF, 'global', '_overrides'), # conf/global_overrides.py
    ListFiles(options.lazy.CONF, options.lazy.SITE, '_overrides'), # conf/<site>_overrides.py
]

def convert_to_options(source, destination):
    for k, v in source.iteritems():
        if isinstance(k, types.ModuleType):
            continue
        if k is options:
            continue
        if not k.isupper():
            continue
        if k.startswith('_'):
            continue
        if isinstance(k, (list, tuple)):
            k = DictList(keys = k)
        if isinstance(k, dict):
            k = DictList(values = k)
        if _DEBUG >= 3: 
            print 'Loading settings key', k, '=', v
        setattr(destination, k, v)

def copy_all(source, destination):
    for opt, value in source.iteritems():
        if opt.isupper():
            if _DEBUG >= 3:
                print 'Updating settings key', opt, '=', value
            destination[opt] = value

def import_from_module(locals, module):
    from django.utils.importlib import import_module
    config = Config()
    mod = import_module(module)
    data = dict([(k, getattr(mod, k)) for k in dir(mod)])
    convert_to_options(data, config)
    copy_all(config, locals)

def autodiscover(locals=None):
    from django.utils.importlib import import_module
    if locals is not None:
        convert_to_options(locals, options)
    
    for files in options.DISCOVERY_ORDER:
        for path, name in files:
            if path.startswith('django.contrib.admin'):
                # django.contrib.admin tries to load django.db.utils,
                # which in turn tries to load settings and fails.
                continue 
            try:
                mod = path+ '.' + name.replace('.', '__') 
                if _DEBUG >= 1:
                    print 'Importing', mod
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
                    if not os.isatty(1):
                        raise
            except Exception:
                print_exc()

    if locals is not None:
        copy_all(options, locals)
