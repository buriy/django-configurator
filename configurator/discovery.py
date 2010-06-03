import socket
import types

def site_name():
    return socket.getfqdn().replace('.','_').replace('-','__')

class ListFiles(object):
    def __init__(self, paths, names, suffix=''):
        self.paths = paths
        self.names = names
        self.suffix = suffix
    
    def __iter__(self):
        for path in self._get_list(self.paths):
            for filename in self._get_list(self.names):
                yield str(path), str(filename) + str(self.suffix)

    def _get_list(self, k):
        if callable(k):
            k = k()
        if isinstance(k, types.StringTypes):
            return [k]
        else:
            return k

    def __repr__(self):
        return "ListFiles(%r, %r, %r)" % (self.paths, self.names, self.suffix)