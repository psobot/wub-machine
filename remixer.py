#!/usr/bin/env python
"""
remixer.py

Provides a basic remix superclass to build music remixers into bigger apps. (i.e.: web apps)
The heart of the Wub Machine (wubmachine.com) and hopefully more to come.

by Peter Sobot <hi@petersobot.com>
    v1: started Jan. 2011
    v2: August-Sept 2011
"""
from numpy import array
from os import rename, unlink, path, access, W_OK
from threading import Thread
from multiprocessing import Queue, Process
from traceback import print_exception, format_exc
from subprocess import check_call, call
from mutagen import File, id3
from PIL import Image
from echonest.selection import *
from echonest.sorting import *
import echonest.audio as audio
import time, sys, wave, mimetypes, config, logging, traceback

class Remixer(Thread):
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
    def __init__(self, parent, infile, outfile=None, callbacks=None):
        """
            Takes in parent (whatever class spawns the remixer), in/out filenames,
            and a UID to identify the remix by.
            Logger should be a non-blocking function that needs to know *all* progress updates.
        """
        #   Thread variables
        if isinstance(callbacks, list):
            self.callbacks =   callbacks
        else:
            self.callbacks =   [callbacks]
        self.being_watched = False #  If nobody is watching, this remix can/should be killed.
        self.parent =    parent
        self.uid =       path.splitext(path.basename(infile))[0]
        self.extension = path.splitext(infile)[-1]
        self.timeout =   600     #   seconds
        self.queue =     None    #   queue between thread and process
        self.errortext = "Sorry, that song didn't work. Try another!"
        self.started =   None
        self.status =    0
        self.added =     time.time()

        #   Remixer variables
        self.keys =      {0: "C", 1: "C#", 2: "D", 3: "Eb", 4: "E", 5:"F", 6:"F#", 7:"G", 8:"G#", 9:"A", 10:"Bb", 11:"B"}
        self.infile  =   str(infile)
        if access('tmp/', W_OK):
            self.tempdir =   'tmp/'
        else:
            self.tempdir =   './'
        self.tempfile =  path.join(self.tempdir, "%s.wav" % self.uid)
        self.outdir =    'static/songs/'
        self.overlay =   'static/img/overlay.png' # Transparent overlay to put on top of song artwork
        self.outfile =   outfile or path.join(path.dirname(self.infile), "%s.out.mp3" % self.uid)
        self.artmime = None
        self.artpath = None
        self.artprocessed = False
        self.progress =  0.0
        self.step =      None
        self.encoded =   0
        self.deleteOriginal = True

        self.sample_path = 'samples/%s/' % str(self.__class__.__name__).lower()
        
        self.tag =       {}      #   Remix metadata tag
        self.original =  None    #   audio.LocalAudioFile-returned analysis
        self.tonic =     None
        self.tempo =     None
        self.bars =      None
        self.beats =     None
        self.sections =  None

        Thread.__init__(self)


    """
        All of the following progress methods should be of the form:
        {
            'status':
                -1 is error
                0 is waiting
                1 is OK
            'uid':
                uid of the track
            'time':
                current timestamp (not yet used)
            'text':
                progress text or user string to display for errors
            'progress':
                0-1 measure of progress, 1 being finished, 0 being not started
            'tag':
                Song-specific tag including all of its metadata
            ['debug']:
                Optional debug info if error.
        }
    """
    def logbase(self):
        return { 'status': self.status, 'text': self.step, 'progress': self.progress, 'tag': self.tag, 'uid': self.uid, 'time': time.time() }

    def log(self, text, progress):
        """
            Pass progress updates back to the run() function, which then bubbles up to everybody watching this remix.
            Automatically increments progress, which can be a fractional percentage or decimal percentage.
        """
        if progress > 1:
            progress *= 0.01
        self.progress += progress
        self.step = text

        self.processqueue.put(self.logbase())

    def handleError(self, e):
        self.step = "Hmm... something went wrong. Please try again later!"
        progress = self.logbase()
        progress['debug'] = unicode(e)
        self.last = progress

    def error(self, text):
        """
            In case of emergency, break glass.
            In case of remixer error, log an error and close the queue.
        """
        self.step = text
        self.status = -1

        update = self.logbase()
        update['text'] = self.errortext
        update['debug'] = text

        self.processqueue.put(update)
        self.close()

    def finish(self, text):
        """
            When the remixing's all done, log it and close the queue.
        """
        self.progress = 1
        self.step = text
        self.processqueue.put(self.logbase())
        self.close()

    def close(self):
        """
            When it's all over, the run() function needs to know when to go home.
        """
        self.processqueue.put(False)

    def stop(self):
        """
            Set status flag to error, which stops the remixing, terminates the child process and returns.
        """
        print "Trying to stop remixer %s" % self.uid
        self.status = -1

    def attach(self, callback): 
        """
            Attaches a given callback to the remix, to be called on the next progress update.
            Intended to send asynchronous updates to a user who's remixing a song. (i.e.: via HTTP)
        """
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def cleanup(self):
        """
            Remove all temporary files, and clear unused memory.
            Remixin's a messy business.
        """
        if path.isfile(self.tempfile):
            unlink(self.tempfile)
        if self.deleteOriginal and path.isfile(self.infile):
            unlink(self.infile)

        i = 0
        f = "%s%s%s.wav" % (self.tempdir, self.uid, i)
        while path.isfile(f):
            unlink(f)
            i += 1
            f = "%s%s%s.wav" % (self.tempdir, self.uid, i)
        if self.original:
            self.original.unload()

    def run(self):
        """
            Spawns a child process to do the actual remixing.
            Blocks until a progress update comes from the child process.
            When a progress update comes through:
                if someone is watching (i.e.: there's a callback) then fire the callback
                if not, put the progress update into a queue
                if somebody is *monitoring* and doesn't care about missing an update,
                  fire the monitors callback. (Useful for watching an entire server of remixers.)
            The "loggers" callback gets fired on each update, no matter what.

            After remixing is complete and the communication queue is closed,
            the subprocess is joined, deleted, and the parent's "finish" method
            is called if it exists.
        """
        self.started = time.time()
        self.status = 1
        self.processqueue = Queue()
        self.p = Process(target=self._remix)                    #   Actual remix process started with Multiprocessing
        self.p.start()

        self.last = None
        try:
            progress = self.processqueue.get(True, self.timeout)          #   Queue that blocks until progress updates happen
            while progress and self.status is not -1:                       #   MUST END WITH False value, or else this will block forever
                self.last = progress
                for callback in self.callbacks:                             #   Send all progress updates
                    callback(progress)
                progress = self.processqueue.get(True, self.timeout)      #   Grab another progress update from the process
        except Exception, e:
            self.status = -1
            self.handleError(e)
        else:
            if self.status is -1:
                try:
                  self.handleError(Exception("RemixTermination. Last was:\n%s" % last))
                except:
                    self.handleError(Exception("RemixTermination"))
        self.processqueue.close()
        self.p.terminate()
        self.cleanup()
        del self.p
        if hasattr(self.parent, 'finish'):
            self.parent.finish(self.uid, self.last)

    def _remix(self):
        """
          Failure-tolerant wrapper around main remix method that allows for cleanup and such.
        """
        try:
            self.tag['style'] = str(self.__class__.__name__)
            self.tag['remixed'] = self.remix()
            self.finish("Done!")
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print_exception(exc_type, exc_value, exc_traceback,limit=4, file=sys.stderr)
            fname = path.split(exc_traceback.tb_frame.f_code.co_filename)[1]
            lines = format_exc().splitlines()
            self.error("%s @ %s:%s\n\n%s" % (exc_value, fname, exc_traceback.tb_lineno, '\n'.join(lines)))
        finally:
            self.cleanup()

    """
    Audio methods for encoding, partial encoding, custom mixing, 
    """
    def lame(self, infile, outfile):
        """
            Use the installed (hopefully latest) build of
            LAME to get a really, really high quality MP3.
        """
        r = check_call(['lame', '-S', '--preset', 'fast', 'medium', str(infile), str(outfile)])
        return r

    def mono_to_stereo(self, audio_data):
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
        newdata = audio.AudioData(ndarray=dataA.data, sampleRate=dataA.sampleRate,
            numChannels=dataA.numChannels, defer=False, verbose=False)
        newdata.data *= float(mix)
        if dataB.endindex > dataA.endindex:
            newdata.data[:] += dataB.data[:dataA.endindex] * (1 - float(mix))
        else:
            newdata.data[:dataB.endindex] += dataB.data[:] * (1 - float(mix))
        return newdata

    def partialEncode(self, audiodata):
        """
            A neat alternative to AudioQuantumList.
            Instead of making a list, holding it in memory and encoding it all at once,
            each element in the list is encoded upon addition.

            After many partialEncode()s, the mixwav() function should be called,
            which calls shntool on the command line for super-fast audio concatenation.
        """
        audiodata.encode("%s%s%03d.wav" % (self.tempdir, self.uid, self.encoded))
        audiodata.verbose = False
        audiodata.unload()
        self.encoded += 1

    def mixwav(self, filename):
        """
            When used after partialEncode(), this concatenates a number of audio
            files into one with a given filename. (Super fast, super memory-efficient.)
            
            Requires the shntool binary to be installed.
        """
        if self.encoded is 1:
            rename("%s%s%03d.wav" % (self.tempdir, self.uid, 0), filename)
            return
        args = ['shntool', 'join', '-z', self.uid, '-q', '-d', self.tempdir]
        for i in xrange(0, self.encoded):
            args.append("%s%s%03d.wav" % (self.tempdir, self.uid, i))
        call(args)
        rename("%sjoined%s.wav" % (self.tempdir, self.uid), filename)
        for i in xrange(0, self.encoded):
            unlink("%s%s%03d.wav" % (self.tempdir, self.uid, i))

    """
    Metadata methods for tagging
    """
    def getTag(self):
        """
            Tries to get the metadata tag from the input file.
            May not work. Only set up to do mp3, m4a and wav.
            Returns its success value as a boolean.
        """
        try:
            self.mt = File(self.infile)
            tag = {}

            # technical track metadata
            if hasattr(self.mt, 'info'):
                tag['bitrate'] = self.mt.info.bitrate if hasattr(self.mt.info, 'bitrate') else None
                tag['length'] = self.mt.info.length if hasattr(self.mt.info, 'length') else None
                tag['samplerate'] = self.mt.info.sample_rate if hasattr(self.mt.info, 'sample_rate') else None
                tag['channels'] = self.mt.info.channels if hasattr(self.mt.info, 'channels') else None
            elif self.extension == ".wav":
                wav = wave.open(self.infile)
                tag['samplerate'] = wav.getframerate()
                tag['channels'] = wav.getnchannels()
                tag['length'] = float(wav.getnframes()) / tag['samplerate']
                tag['bitrate'] = (wav._file.getsize() / tag['length']) / 0.125  # value in kilobits
                wav.close()
                del wav

            if self.mt:
                if self.extension == ".mp3":
                    if 'TIT2' in self.mt: tag["title"] = self.mt['TIT2'].text[0]
                    if 'TPE1' in self.mt: tag["artist"] = self.mt['TPE1'].text[0]
                    if 'TALB' in self.mt: tag["album"] = self.mt['TALB'].text[0]
                elif self.extension == ".m4a":
                    if '\xa9nam' in self.mt: tag["title"] = self.mt['\xa9nam'][0]
                    if '\xa9ART' in self.mt: tag["artist"] = self.mt['\xa9ART'][0]
                    if '\xa9alb' in self.mt: tag["album"] = self.mt['\xa9alb'][0]

            self.tag = dict(self.tag.items() + tag.items()) # Merge all new tags into tag object
            if hasattr(self.parent, 'updateTrack'):
                self.parent.updateTrack(self.uid, tag)
            return True
        except:
            return False

    def detectSong(self, analysis):
        """
            Uses an EchoNest analysis to try to detect the name and tag info of a song.
        """
        try:
            for k in ['title', 'artist', 'album']:
                if k in self.original.analysis.metadata and not k in self.tag:
                    self.tag[k] = self.original.analysis.metadata[k]
        except:
           pass


    def processArt(self):
        """
            Tries to parse artwork from the incoming file.
            Saves artwork in a configurable location, along with a thumbnail.
            Useful for web frontends and the like.
            If an overlay is provided, that overlay is pasted on top of the artwork.

            Returns success value as a boolean.
        """
        try:
            if not self.mt:
                return False
            imgmime = False
            imgdata = False
            if self.extension == ".mp3":
                if "APIC:" in self.mt:
                    imgmime = self.mt['APIC:'].mime
                    imgdata = self.mt['APIC:'].data
            elif self.extension == ".m4a":
                if "covr" in self.mt:
                    if self.mt['covr'][0][0:4] == '\x89PNG':
                        imgmime = u'image/png'
                    elif self.mt['covr'][0][0:10] == '\xff\xd8\xff\xe0\x00\x10JFIF':  # I think this is right...
                        imgmime = u'image/jpeg'
                    imgdata = self.mt['covr'][0]
            if imgmime and imgdata:
                self.artmime = imgmime
                ext = mimetypes.guess_extension(imgmime)
                if not ext:
                    raise Exception("Unknown artwork format!")
                artname = path.join(self.tempdir, "%s%s" % (self.uid, ext))
                self.artpath = path.join(self.outdir, "%s%s" % (self.uid, ext))
                self.thumbpath = path.join(self.outdir, "%s.thumb%s" % (self.uid, ext))

                artwork = open(artname, "w")
                artwork.write(imgdata)
                artwork.close()
                
                if self.overlay:
                    overlay = Image.open(self.overlay)
                    artwork = Image.open(artname).resize(overlay.size, Image.BICUBIC)
                    artwork.paste(overlay, None, overlay)

                artwork.save(self.artpath)
                artwork.resize((config.thumbnail_size,config.thumbnail_size), Image.ANTIALIAS).convert("RGB").save(self.thumbpath)

                unlink(artname)

                self.tag["art"] = self.artpath
                self.tag["thumbnail"] = self.thumbpath
                self.artprocessed = True
                if hasattr(self.parent, 'updateTrack'):
                    self.parent.updateTrack(self.uid, self.tag)
                return True
        except:
            logging.getLogger().warning("Artwork processing failed for %s:\n%s" % (self.uid, traceback.format_exc()))
            self.artprocessed = False
            return False

    def updateTags(self, titleSuffix=''):
        """
            Updates the MP3 tag.
            Can use a mutagen tag (mt) from an MP3 or an M4A.
        """
        try:
            self.tag['new_title'] = "%s%s" % (
              (self.tag['title']
                if ('title' in self.tag and self.tag['title'].strip() != '')
                else '[untitled]'),
              titleSuffix
            )

            if 'TIT2' in self.mt:
                self.mt['TIT2'].text[0] += titleSuffix
            elif '\xa9nam' in self.mt:
                self.mt['\xa9nam'][0] += titleSuffix

            outtag = File(self.outfile)  
            outtag.add_tags()
            outtag.tags.add(id3.TBPM(encoding=0, text=unicode(self.template['tempo'])))
            if self.extension == ".mp3":
                for k, v in self.mt.iteritems():
                    if k != 'APIC:':
                        outtag.tags.add(v)
            elif self.extension == ".m4a":
                tags = {
                    '\xa9alb': id3.TALB,
                    '\xa9ART': id3.TPE1,
                    '\xa9nam': id3.TIT2,
                    '\xa9gen': id3.TCON                    
                }
                for k, v in self.mt.iteritems():
                    if k in tags:
                        outtag.tags.add(tags[ k ](encoding=0, text=v[0]))
                if 'trkn' in self.mt:
                    if type(self.mt['trkn'][0] == tuple):
                        outtag.tags.add(id3.TRCK(encoding=0, text=("%s/%s" % (self.mt['trkn'][0][0], self.mt['trkn'][0][1]))))
                    else:
                        outtag.tags.add(id3.TRCK(encoding=0, text=(self.mt['trkn'][0])))
                if 'disk' in self.mt:
                    if type(self.mt['disk'][0] == tuple):
                        outtag.tags.add(id3.TPOS(encoding=0, text=("%s/%s" % (self.mt['disk'][0][0], self.mt['disk'][0][1]))))
                    else:
                        outtag.tags.add(id3.TPOS(encoding=0, text=(self.mt['disk'][0])))     

            if self.artprocessed:
                outtag.tags.add(
                    id3.APIC(
                        encoding=3, # 3 is for utf-8
                        mime=self.artmime, # image/jpeg or image/png
                        type=3, # 3 is for the cover image
                        desc=u'Cover',
                        data=open(self.artpath).read()
                    )
                )
            outtag.save()
        except:
            pass

    def loudness(self, segments, bar):
        """
            Given a list of segments (a.k.a: song.analysis.segments) and a bar,
            calculate the average loudness of the bar.
        """
        b = segments.that(overlap_range(bar[0].start, bar[len(bar)-1].end))
        maximums = [x.loudness_max for x in b]
        if len(maximums):   
            return float(sum(maximums) / len(maximums))
        else:
            return None


class CMDRemix():
    """
        Remix from the command line with this handy little class.
        Instantiate this class from any remixer, and this wraps around
        the remixer, pushes progress updates to the console, and allows
        command line based remixing. Very basic, but useful.

        Instantiate the class, but don't try to call any functions, i.e.:
            if __name__ == "__main__":
                CMDRemix(Dubstep)
        will handle all command line remixing for the "Dubstep" remixer.
    """
    def __init__(self, remixer):
        """
            Handles command line argument parsing and sets up a new remixer.
        """
        if len(sys.argv) < 2:
            print "Error: no file specified!"
            print "Usage: python -m remixers.%s <song.[mp3|m4a|wav|aif]>" % str(remixer.__name__.lower())
        elif not path.exists(sys.argv[1]):
            print "Error: song does not exist!"
        else:
            r = remixer(self, sys.argv[1], callbacks=self.log)
            r.deleteOriginal = False
            r.start()
            r.join()

    def log(self, s):
        """
            Prints progress updates to the console.
        """
        print "(%s%%) %s" % (round(s['progress']*100, 2), s['text']) 

if __name__ == "__main__":
    raise Exception("This class is a superclass of all remixers. Call the appropriate remixer instead.")
