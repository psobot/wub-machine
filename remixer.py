#!/usr/bin/env python
"""
remixer.py

Provides a basic remix superclass to build music remixers into bigger apps. (i.e.: web apps)
The heart of the Wub Machine (wubmachine.com) and hopefully more to come.

by Peter Sobot <hi@petersobot.com>
    v1: started Jan. 2011
    v2: August 2011
"""
from numpy import array
from os import rename, unlink, path, access, W_OK
from threading import Thread
from multiprocessing import Queue, Process
from subprocess import check_call, call
from mutagen import File, id3
import echonest.audio as audio
import time, sys

class Remixer( Thread ):
    """
        Generic song remixer to be inherited from and
        embedded in something bigger - i.e. a web app.
        (like the Wub Machine...)

        Inherits from Thread to allow for asynchronous processing.

        Workhorse function (run()) spawns a child process for the remixer,
        then blocks for progress updates and calls callback functions when they occur.
        Progress updates are kept in a queue and callbacks fired immediately if the
        queue is not empty. Otherwise, the callback is fired when the progress update comes in.

        Child process is used for memory efficiency and to leverage multiple cores better.
        Spawn 4 remixers on a quad-core machine, and remix 4 tracks at once!

        Includes convenience methods for all remixers to use, as well as metadata functions
        and a memory-light alternative to AudioQuantumList: partialEncode().
    """
    def __init__( self, parent, infile, outfile, extension, uid, requester=None, logging=None ):
        """
            Takes in parent (whatever class spawns the remixer), in/out filenames,
            file extension (that seems redundant...), a UID to identify the remix by,
            optional requester (used for IP tracking in the web frontend) and logger.

            Logger should be a non-blocking function that needs to know *all* progress updates.
        """
        #   Thread variables
        self.callbacks = []
        self.logging =   logging
        self.requester = requester
        self.parent =    parent
        self.uid =       uid
        self.extension = extension
        self.timeout =   600     #   seconds
        self.queue =     None    #   queue between thread and process
        self.errortext = "Whoops... that didn't work. Try another song!"
        self.started =   None

        #   Remixer variables
        self.keys =      {0: "C", 1: "C#", 2: "D", 3: "Eb", 4: "E", 5:"F", 6:"F#", 7:"G", 8:"G#", 9:"A", 10:"Bb", 11:"B"}
        self.infile  =   infile
        if access( 'temp/', W_OK ):
            self.tempdir =   'temp/'
        else:
            self.tempdir =   './'
        self.tempfile = path.join( self.tempdir, self.uid + ".wav" )
        self.outfile =   outfile
        self.progress =  0.0
        self.step =      None
        self.encoded =   0
        self.deleteOriginal = True

        self.tag =       {}      #   MP3 or AAC tag
        self.original =  None    #   audio.LocalAudioFile-returned analysis
        self.tonic =     None
        self.tempo =     None
        self.bars =      None
        self.beats =     None
        self.sections =  None

        Thread.__init__( self )

    def log( self, text, progress ):
        """
            Pass progress updates back to the run() function, which then bubbles up to everybody watching this remix.
            Automatically increments progress, which can be a fractional percentage or decimal percentage.
        """
        if progress > 1:
            progress *= 0.01
        self.progress += progress
        self.step = text
        self.processqueue.put( { "text": text, 'progress': self.progress, 'tag': self.tag, 'uid': self.uid, 'time': time.time() } )

    def error( self, text ):
        """
            In case of emergency, break glass.
            In case of remixer error, log an error and close the queue.
        """
        self.step = text
        self.processqueue.put( { "error": self.errortext, 'progress': -1, 'tag': self.tag, 'uid': self.uid, 'debug': str( text ), 'time': time.time() } )
        self.close()

    def finish( self, text ):
        """
            When the remixing's all done, log it and close the queue.
        """
        self.progress = 1
        self.step = text
        self.processqueue.put( { "text": text, 'progress': self.progress, 'tag': self.tag, 'uid': self.uid, 'time': time.time() } )
        self.close()

    def close( self ):
        """
            When it's all over, the run() function needs to know when to go home.
        """
        self.processqueue.put( False )

    def attach( self, callback ):       #   Might want to move this, and the listenqueue, to the RemixQueue class
        """
            Attaches a given callback to the remix, to be called on the next progress update.
            If there are waiting updates in the listenqueue, fire the callback immediately.
        """
        if len( self.listenqueue ):
            callback( self.listenqueue.pop(0) )
        elif callback not in self.callbacks:
            self.callbacks.append( callback )

    def cleanup( self ):
        """
            Remove all temporary files, and clear unused memory.
            Remixin's a messy business.
        """
        if path.isfile( self.tempfile ):
            unlink( self.tempfile )
        if self.deleteOriginal and path.isfile( self.infile ):
            unlink( self.infile )
        for i in xrange( 0, self.encoded ):
            f = "%s%s%s.wav" % ( self.tempdir, self.uid, i )
            if path.isfile( f ):
                unlink( f )
        if self.original:
            self.original.unload()

    def run( self ):
        """
            Spawns a child process to do the actual remixing.
            Blocks until a progress update comes from the child process.
            When a progress update comes through:
                if someone is watching (i.e.: there's a callback) then fire the callback
                if not, put the progress update into a queue
            The "logging" callback gets fired on each update, no matter what.

            After remixing is complete and the communication queue is closed,
            the subprocess is joined, deleted, and the parent's "finish" method
            is called if it exists.
        """
        self.started = time.time()
        self.processqueue = Queue()
        self.listenqueue = []
        p = Process( target=self.remix )                    #   Actual remix thread started with Multiprocessing
        p.start()

        self.last = None
        try:
            progress = self.processqueue.get( True, self.timeout )          #   Queue that blocks until progress updates happen
            while progress:                                                 #   MUST END WITH False value, or else this will block forever
                self.last = progress
                if not self.callbacks:                                      #   If nobody's currently waiting on a progress update, put in listenqueue
                    self.listenqueue.append( progress ) 
                while self.callbacks:                                       #   If anybody is watching, then call them back immediately
                    self.callbacks.pop()( progress )
                if self.logging:                                            #   If we're logging, call the logging function
                    self.logging( progress )
                progress = self.processqueue.get( True, self.timeout )      #   Grab another progress update from the process
        except Exception, e:
            progress = { "error": "Hmm... Remixing is too slow right now. Please try again later!", "progress": -1 }
            self.last = progress

        for callback in self.callbacks:
            callback( self.last )                            #   Some "Finished" callback just to kill all possible listeners
        p.join()
        del p
        if hasattr( self.parent, 'finish' ):
            self.parent.finish( self.uid, self.last )

    """
    Audio methods for encoding, partial encoding, custom mixing, 
    """
    def lame( self, infile, outfile ):
        """
            Use the installed (hopefully latest) build of
            LAME to get a really, really high quality MP3.
        """
        r = check_call( ['lame', '-S', '--preset', 'fast', 'medium', str( infile ), str( outfile )] )
        return r

    def mono_to_stereo( self, audio_data ):
        """
            Take in an AudioData with two channels,
            return one with one. This here's a theivin' method.
        """
        data = audio_data.data.flatten().tolist()
        new_data = array((data,data))
        audio_data.data = new_data.swapaxes(0,1)
        audio_data.numChannels = 2
        return audio_data

    def truncatemix(self, dataA, dataB, mix=0.5):
        """
        Mixes two "AudioData" objects. Assumes they have the same sample rate
        and number of channels.
        
        Mix takes a float 0-1 and determines the relative mix of two audios.
        i.e., mix=0.9 yields greater presence of dataA in the final mix.

        If dataB is longer than dataA, dataB is truncated to dataA's length.
        """
        newdata = audio.AudioData(ndarray=dataA.data, sampleRate=dataA.sampleRate, numChannels=dataA.numChannels, defer=False, verbose=False)
        newdata.data *= float(mix)
        if dataB.endindex > dataA.endindex:
            newdata.data[:] += dataB.data[:dataA.endindex] * (1 - float(mix))
        else:
            newdata.data[:dataB.endindex] += dataB.data[:] * (1 - float(mix))
        return newdata

    def partialEncode( self, audiodata ):
        """
            A neat alternative to AudioQuantumList.
            Instead of making a list, holding it in memory and encoding it all at once,
            each element in the list is encoded upon addition.

            After many partialEncode()s, the mixwav() function should be called,
            which calls shntool on the command line for super-fast audio concatenation.
        """
        audiodata.encode( "%s%s%s.wav" % ( self.tempdir, self.uid, self.encoded ) )
        audiodata.verbose = False
        audiodata.unload()
        self.encoded += 1

    def mixwav( self, filename ):
        """
            When used after partialEncode(), this concatenates a number of audio
            files into one with a given filename. (Super fast, super memory-efficient.)
            
            Requires the shntool binary to be installed.
        """
        args = ['shntool', 'join', '-z', self.uid, '-q', '-d', self.tempdir]
        for i in xrange( 0, self.encoded ):
            args.append( "%s%s%s.wav" % ( self.tempdir, self.uid, i ) )
        call( args )
        rename( "%sjoined%s.wav" % ( self.tempdir, self.uid ), filename )
        for i in xrange( 0, self.encoded ):
            unlink( "%s%s%s.wav" % ( self.tempdir, self.uid, i ) )
        return filename

    """
    Metadata methods for 
    """
    def getTag( self ):
        """
            Tries to get the metadata tag from the input file.
            May not work. Only set up to do mp3 and m4a.
            Returns its success value as a boolean.
        """
        try:
            self.mt = File( self.infile )
            tag = {}
            if self.extension == ".mp3":
                tag["title"] = self.mt['TIT2'].text[0]
                tag["artist"] = self.mt['TPE1'].text[0]
                tag["album"] = self.mt['TALB'].text[0]
            elif self.extension == ".m4a":
                tag["title"] = self.mt['\xa9nam'][0]
                tag["artist"] = self.mt['\xa9ART'][0]
                tag["album"] = self.mt['\xa9alb'][0]
            else:
                raise Exception( "No tags found!" )
            self.tag = tag
            return True
        except:
            return False

class CMDRemix():
    """
        Remix from the command line with this handy little class.
        Instantiate this class from any remixer, and this wraps around
        the remixer, pushes progress updates to the console, and allows
        command line based remixing. Very basic, but useful.

        Instantiate the class, but don't try to call any functions, i.e.:
            if __name__ == "__main__":
                CMDRemix( Dubstep )
        will handle all command line remixing for the "Dubstep" remixer.
    """
    def __init__( self, remixer ):
        """
            Handles command line argument parsing and sets up a new remixer.
        """
        if len( sys.argv ) < 2:
            print "Error: no file specified!"
            print "Usage: %s <song.[mp3|m4a|wav|aif]>" % sys.argv[0]
        elif not path.exists( sys.argv[1] ):
            print "Error: song does not exist!"
        else:
            r = remixer( self, sys.argv[1], path.splitext(sys.argv[1])[0] + '.wub.mp3', path.splitext(sys.argv[1])[-1], "console", logging=self.log )
            r.deleteOriginal = False
            r.start()
            r.join()

    def log( self, s ):
        """
            Prints progress updates to the console.
        """
        print "(%s%%) %s" % ( round( s['progress']*100, 2 ), s['text'] ) 

if __name__ == "__main__":
    raise Exception( "This class is a superclass of all remixers. Call the appropriate remixer instead." )
