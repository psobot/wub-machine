import sys
class config(object):
    import yaml, uuid, os, logging
    """
        Magical config class that allows for real-time updating of config variables.
        Every attribute access to this class (i.e.: config.config.thumbnail_size) will
        check the fmod time of the config YAML file, and read the file if necessary.

        Fast, although it does an os.stat on every attribute access. Worth it.
    """

    # Format of track identifiers (currently UUIDs)
    uid = lambda(self): str( object.__getattribute__(self, 'uuid').uuid4() ).replace( '-', '' )
    uid_re = r'[a-f0-9]{32}'

    last_updated = 0
    config_file = 'config.yml'
    
    def __init__(self):
        # Variables to be passed through to javascript.
        self.javascript = {
            'socket_io_port': self.socket_io_port,
            'remember_transport': False,
            'monitor_resource': self.monitor_resource,
            'progress_resource': self.progress_resource,
            'socket_extra_sep': self.socket_extra_sep,
            'allowed_file_extensions': [x[1:] for x in self.allowed_file_extensions],
            'drop_text': 'Drop a song here to remix!',
            'upload_text': 'Click here (or drag in a song) to create a remix.',
            'soundcloud_consumer': self.soundcloud_consumer,
            'soundcloud_redirect': self.soundcloud_redirect,
        }

    def update(self, filename=None):
        """
            Update the object's attributes.
        """
        object.__getattribute__(self, 'logging').getLogger().info("Config file has changed, updating...")
        if not filename:
            filename = object.__getattribute__(self, 'config_file')
        for k, v in object.__getattribute__(self, 'yaml').load(open(filename)).iteritems():
            setattr(self, k, v)

    def __getattribute__(self, name):
        """
            When trying to access an attribute, check if the underlying file has changed first.
        """
        if name in ['update', 'javascript', 'uid', 'uid_re']:
            return object.__getattribute__(self, name)
        else:
            last_updated = object.__getattribute__(self, 'last_updated')
            fmod_time = object.__getattribute__(self, 'os').stat(object.__getattribute__(self, 'config_file'))[9]
            if last_updated < fmod_time:
                self.last_updated = fmod_time
                self.update()
            return object.__getattribute__(self, name)

# This is a dirty, dirty hack, but lets you just do:
#   import config
# and have access to an instantiated config object.
sys.modules[__name__] = config()
