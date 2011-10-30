import os, mimetools, itertools, mimetypes

class Daemonize():
    # Default daemon parameters.
    # File mode creation mask of the daemon.
    UMASK = 0
    # Default working directory for the daemon.
    WORKDIR = os.getcwd()
    # Default maximum for the number of available file descriptors.
    MAXFD = 1024
    # The standard I/O file descriptors are redirected to /dev/null by default.
    def __init__( self ):
        """Detach a process from the controlling terminal and run it in the
        background as a daemon.
        """
        if ( hasattr( os, "devnull" ) ):
           REDIRECT_TO = os.devnull
        else:
           REDIRECT_TO = "/dev/null"
        try:
            pid = os.fork()
        except OSError, e:
            raise Exception, "%s [%d]" % ( e.strerror, e.errno )

        if (pid == 0):	# The first child.
            os.setsid()
            try:
                pid = os.fork()	# Fork a second child.
            except OSError, e:
                raise Exception, "%s [%d]" % ( e.strerror, e.errno )

            if (pid == 0):	# The second child.
                os.chdir( self.WORKDIR )
                #os.umask( self.UMASK )
            else:
                os._exit( 0)
        else:
            os._exit( 0 )	# Exit parent of the first child.
        import resource		# Resource usage information.
        maxfd = resource.getrlimit( resource.RLIMIT_NOFILE )[1]
        if ( maxfd == resource.RLIM_INFINITY ):
            maxfd = self.MAXFD

        # Iterate through and close all file descriptors.
        for fd in xrange( 0, maxfd ):
            try:
                os.close(fd)
            except OSError:	# ERROR, fd wasn't open to begin with (ignored)
                pass
        os.open( REDIRECT_TO, os.O_RDWR )	# standard input (0)

        # Duplicate standard input to standard output and standard error.
        os.dup2(0, 1)			# standard output (1)
        os.dup2(0, 2)			# standard error (2)

class MultiPartForm(object):
    """Accumulate the data to be used when posting a form."""

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = mimetools.choose_boundary()
        return

    def get_content_type(self):
        return 'multipart/form-data; boundary=%s' % self.boundary

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, value))
        return

    def add_file(self, fieldname, filename, fileHandle, mimetype=None):
        """Add a file to be uploaded."""
        body = fileHandle.read()
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.files.append((fieldname, filename, mimetype, body))
        return

    def __str__(self):
        """Return a string representing the form data, including attached files."""
        # Build a list of lists, each containing "lines" of the
        # request.  Each part is separated by a boundary string.
        # Once the list is built, return a string where each
        # line is separated by '\r\n'.  
        parts = []
        part_boundary = '--' + self.boundary

        # Add the form fields
        parts.extend(
            [ part_boundary,
              'Content-Disposition: form-data; name="%s"' % str( name ),
              '',
              str( value ),
            ]
            for name, value in self.form_fields
            )

        # Add the files to upload
        parts.extend(
            [ part_boundary,
              'Content-Disposition: file; name="%s"; filename="%s"' % \
                 ( str( field_name ), str( filename ) ),
              'Content-Type: %s' % str( content_type ),
              '',
              str( body ),
            ]
            for field_name, filename, content_type, body in self.files
            )

        # Flatten the list and add closing boundary marker,
        # then return CR+LF separated data
        flattened = list(itertools.chain(*parts))
        flattened.append('--' + self.boundary + '--')
        flattened.append('')
        return '\r\n'.join(flattened)

def time_ago_in_words( time = None ):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    from datetime import datetime, timedelta
    now = datetime.now()
    if type( time ) is int:
        diff = now - datetime.fromtimestamp( time )
    elif isinstance( time, datetime ):
        diff = now - time 
    elif isinstance( time, timedelta ):
        diff = now - timedelta
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return  "a minute ago"
        if second_diff < 3600:
            return str( second_diff / 60 ) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str( second_diff / 3600 ) + " hours ago"
    if day_diff == 1:
        return "yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff/7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff/30) + " months ago"
    return str(day_diff/365) + " years ago"

def time_in_words( time = None ):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    if time < 10:
        return "just now"
    if time < 60:
        return str(time) + " seconds"
    if time < 120:
        return  "a minute"
    if time < 3600:
        return str( time / 60 ) + " minutes"
    if time < 7200:
        return "an hour"
    if time < 86400:
        return str( time / 3600 ) + " hours"

def seconds_to_time( time ):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    if not time:
        return "0s"
    from datetime import datetime, timedelta
    if isinstance( time, timedelta ) or isinstance( time, datetime ):
        if time.days < 0:
            diff = timedelta( )
        else:
            diff = time
    else:
        diff = timedelta( seconds = int(time if time >= 0 else 0) )

    second_diff = diff.seconds
    if second_diff < 0:
        second_diff = 0

    if second_diff > 60:
        return "%sm%ss" % ( str( second_diff / 60 ), ( second_diff % 60 ) )
    else:
        return "%ss" % second_diff

def convert_bytes(bytes):
    try:
        bytes = float(bytes)
        if bytes >= 1099511627776:
            terabytes = bytes / 1099511627776
            size = '%.2fTb' % terabytes
        elif bytes >= 1073741824:
            gigabytes = bytes / 1073741824
            size = '%.2fGb' % gigabytes
        elif bytes >= 1048576:
            megabytes = bytes / 1048576
            size = '%.2fMb' % megabytes
        elif bytes >= 1024:
            kilobytes = bytes / 1024
            size = '%.2fKb' % kilobytes
        else:
            size = '%.2fb' % bytes
        return size
    except:
        return "? Kb"

def list_in_words( l ):
    return "%s and %s" % (', '.join(l[:-1]), l[-1])

def ordinal(number):
    suffixes = { 0:'th', 1:'st', 2:'nd', 3:'rd' }
    numstring = str(number)
    if numstring[-2:len(numstring)] in ('11','12') or number % 10 > 3:
        return numstring + 'th'
    else:
        return numstring + suffixes[number % 10]
