"""
dubstep.py <ex: dubstepize.py, wubmachine.py, wubwub.py, etc...>

Turns a song into a dubstep remix.
Dubstep inherits from the Remixer class.
Dependencies:
    FastModify
    Remixer
    lame (command line binary)
    shntool (command line binary)
    soundstretch (command line binary)

by Peter Sobot <hi@petersobot.com>
    v1: started Jan. 2011
    v2: August 2011

originally based off of code by Ben Lacker, 2009-02-24.
"""

from os import unlink
from fastmodify import FastModify
from traceback import print_exception, format_exc
from mutagen import File
from mutagen import id3
from PIL import Image
from echonest.selection import *
from echonest.sorting import *
from remixer import Remixer, CMDRemix
import echonest.audio as audio, sys

class Dubstep( Remixer ):
    """
        The heart of the Wub Machine. The wubalizer, the dubstepper - or the Dubstep class, as it's now been refactored.
        Inherits from Remixer. Call the remix() method to start a remix. (This is forked and called by RemixQueue in the web interface.)
        Template defined in the self.template object: tempo and locations of audio samples.

        A couple custom modifications to the Remix API:
            FastModify is used instead of Modify, which requires the `soundstretch` binary to be installed.
            Remixer.partialEncode() and Remixer.mixwav() are used instead of an AudioQuantumList,
            to save memory and increase processing speed at the expense of disk space. (Requires `shntool` binary.)
            
    """
    template = {
        'tempo':        140,
        'intro':        'samples/dubstep/intro-eight.wav',
        'hats':         'samples/dubstep/hats.wav',
        'wubs':         [   'samples/dubstep/wubs/c.wav',
                            'samples/dubstep/wubs/c-sharp.wav',
                            'samples/dubstep/wubs/d.wav',
                            'samples/dubstep/wubs/d-sharp.wav',
                            'samples/dubstep/wubs/e.wav',
                            'samples/dubstep/wubs/f.wav',
                            'samples/dubstep/wubs/f-sharp.wav',
                            'samples/dubstep/wubs/g.wav',
                            'samples/dubstep/wubs/g-sharp.wav',
                            'samples/dubstep/wubs/a.wav',
                            'samples/dubstep/wubs/a-sharp.wav',
                            'samples/dubstep/wubs/b.wav'
                        ],
        'wub_breaks':   [   'samples/dubstep/break-ends/c.wav',
                            'samples/dubstep/break-ends/c-sharp.wav',
                            'samples/dubstep/break-ends/d.wav',
                            'samples/dubstep/break-ends/d-sharp.wav',
                            'samples/dubstep/break-ends/e.wav',
                            'samples/dubstep/break-ends/f.wav',
                            'samples/dubstep/break-ends/f-sharp.wav',
                            'samples/dubstep/break-ends/g.wav',
                            'samples/dubstep/break-ends/g-sharp.wav',
                            'samples/dubstep/break-ends/a.wav',
                            'samples/dubstep/break-ends/a-sharp.wav',
                            'samples/dubstep/break-ends/b.wav'
                        ],
        'splashes':     [   'samples/dubstep/splashes/splash_03.wav',
                            'samples/dubstep/splashes/splash_04.wav',
                            'samples/dubstep/splashes/splash_02.wav',
                            'samples/dubstep/splashes/splash_01.wav',
                            'samples/dubstep/splashes/splash_05.wav',
                            'samples/dubstep/splashes/splash_07.wav',
                            'samples/dubstep/splashes/splash_06.wav',
                            'samples/dubstep/splashes/splash_08.wav',
                            'samples/dubstep/splashes/splash_10.wav',
                            'samples/dubstep/splashes/splash_09.wav',
                            'samples/dubstep/splashes/splash_11.wav'
                        ],
        'splash_ends':  [   'samples/dubstep/splash-ends/1.wav',
                            'samples/dubstep/splash-ends/2.wav',
                            'samples/dubstep/splash-ends/3.wav',
                            'samples/dubstep/splash-ends/4.wav'
                        ]
    }
    target =    "beats"
    samples =   {}
    mixpoint =  15 # "db factor" of wubs - 0 is soft, infinity is... untested 
    st = None

    def loudness( self, segments, bar ):
        """
            Given a list of segments (a.k.a: song.analysis.segments) and a bar,
            calculate the average loudness of the bar.
        """
        b = segments.that( overlap_range( bar[0].start, bar[len(bar)-1].end ) )
        maximums = [x.loudness_max for x in b]
        if len( maximums ):   
            return float( sum( maximums ) / len( maximums ) )
        else:
            return None

    def searchSamples( self, j, key ):
        """
            Hacky method to find all samples (beats) of a given key in a given section.
        """
        tries = 0
        a = self.getSamples( self.sections[j], key )
        while not len( a ) and tries < 5:
            if tries < 4:
                key = (key + 7) % 12
            else:
                key = tries % 4
            tries = tries + 1
            a = self.getSamples( self.sections[j], key )
       
        tries = 0
        while not len( a ) and tries < 5:    #find-some-samples mode
            j = ( j + 1 ) % len( self.sections )
            key = ( key + 2 ) % 12
            tries = tries + 1
            a = self.getSamples( self.sections[j], key )

        return a

    def chooseSamples( self, target="beats" ):
        """
            Deprecated method that pre-computes a multidimensional array of samples.
            Worked, but was too slow, and 75% of the computed samples were never used.
        """
        #   This could probably be sped up
        for i, section in enumerate(self.sections):
            self.samples[i] = {}
            for pitch in xrange(0, 12):
                self.samples[i][pitch] = self.getSamples( self.sections[i], pitch, target )

    def getSamples( self, section, pitch, target="beats" ):
        """
            The EchoNest-y workhorse. Finds all beats/bars in a given section, of a given pitch.
        """
        sample_list = audio.AudioQuantumList()
        if target == "beats":
            sample_list.extend( [b for x in section.children() for b in x.children()] );
        elif target == "bars":
            sample_list.extend( section.children() )
        return sample_list.that( overlap_ends_of( self.original.analysis.segments.that( have_pitch_max( pitch ) ).that( overlap_starts_of( sample_list ) ) ) )

    def mixfactor( self, segment ):
        """
            Computes a rough "mixfactor" - the balance between wubs and original audio for a given segment.
            Result can be fed into echonest.audio.mix() as the third parameter.
        """
        mixfactor = 0
        a = (float(74)/float(3)) + self.mixpoint
        b = (float(148)/float(3)) + self.mixpoint
        loud = self.loudness( self.original.analysis.segments, segment )
        if not loud:
            loud = self.original.analysis.loudness
        if loud != -1 * b:
            mixfactor = float(float(loud + a)/float(loud + b))
        if mixfactor > 0.8:
            mixfactor = 0.8
        elif mixfactor < 0.3:
            mixfactor = 0.3
        return mixfactor

    def compileIntro( self ):
        """
            Compiles the dubstep introduction. Returns an AudioData of the first 8 bars.
            (8 bars at 140 bpm = ~13.71 seconds of audio)
            If song is not 4/4, tries to even things out by speeding it up by the appropriate amount.

            Pattern:
                first 4 bars of song
                first beat of 1st bar x 4   (quarter notes)
                first beat of 2nd bar x 4   (quarter notes)
                first beat of 3rd bar x 8   (eighth notes)
                first beat of 4th bar x 8   (sixteenth notes)
                third beat of 4th bar x 8   (sixteenth notes)
        """
        out = audio.AudioQuantumList()
        intro = audio.AudioData( self.template['intro'], sampleRate=44100, numChannels=2, verbose=False )
        
        #   First 4 bars of song
        custom_bars = []
        for i in xrange(0, 4):
            custom_bars.append( self.beats[i*4:(i*4)+4] )
        out.extend([x for bar in custom_bars for x in bar])

        #   First beat of first bar x 4
        for i in xrange(0, 4):
            out.append(custom_bars[0][0])
        
        #   First beat of second bar x 4
        for i in xrange(0, 4):
            out.append(custom_bars[1][0])

        beatone = custom_bars[2][0]
        beattwo = custom_bars[3][0]
        beatthree = custom_bars[3][2]
        
        #   First beat of third bar x 8
        for x in xrange(0, 8):
            out.append( audio.AudioQuantum( beatone.start, beatone.duration/2, None, beatone.confidence, beatone.source ) )

        #   First beat of fourth bar x 8
        for x in xrange(0, 8):
            out.append( audio.AudioQuantum( beattwo.start, beattwo.duration/4, None, beattwo.confidence, beattwo.source ) )

        #   Third beat of fourth bar x 8
        for x in xrange(0, 8):
            out.append( audio.AudioQuantum( beatthree.start, beatthree.duration/4, None, beatthree.confidence, beatthree.source ) )

        if self.original.analysis.time_signature == 4:
            shifted = self.st.shiftTempo( audio.getpieces( self.original, out ), self.template['tempo']/self.tempo )
        else:
            shifted = audio.getpieces( self.original, out )
            shifted = self.st.shiftTempo( shifted, len( shifted ) / ( ( 44100 * 16 * 2 * 60.0 )/self.template['tempo'] ) )
        if shifted.numChannels == 1:    
            shifted = self.mono_to_stereo( shifted )
        return self.truncatemix( intro, shifted, self.mixfactor( out ) )

    def compileSection( self, j, section, hats ):
        """
            Compiles one "section" of dubstep - that is, one section (verse/chorus) of the original song,
            but appropriately remixed as dubstep.

            Chooses appropriate samples from the section of the original song in three keys (P1, m3, m7)
            then plays them back in order in the generic "dubstep" pattern (all 8th notes):

            |                         |                         :|
            |: 1  1  1  1  1  1  1  1 | m3 m3 m3 m3 m7 m7 m7 m7 :| x2
            |                         |                         :|

            On the first iteration, the dubstep bar is mixed with a "splash" sound - high-passed percussion or whatnot.
            On the second iteration, hats are mixed in on the offbeats and the wubs break on the last beat to let the
            original song's samples shine through for a second, before dropping back down in the next section.

            If samples are missing of one pitch, the searchSamples algorithm tries to find samples
            a fifth from that pitch that will sound good. (If none exist, it keeps trying, in fifths up the scale.)
            
            If the song is not 4/4, the resulting remix is sped up or slowed down by the appropriate amount.
            (That can get really wonky, but sounds cool sometimes, and fixes a handful of edge cases.)
        """
        onebar = audio.AudioQuantumList()

        s1 = self.searchSamples( j, self.tonic )
        s2 = self.searchSamples( j, (self.tonic + 3) % 12 )
        s3 = self.searchSamples( j, (self.tonic + 9) % 12 )

        biggest = max( [s1, s2, s3] ) #for music that's barely tonal
        if not biggest:
            for i in xrange( 0, 12 ):
                biggest = self.searchSamples( j, self.tonic + i )
                if biggest:
                    break

        if not biggest:
            raise Exception( 'Missing samples in section %s of the song!' % j+1 )

        if not s1: s1 = biggest
        if not s2: s2 = biggest
        if not s3: s3 = biggest

        if self.target == "tatums":
            f = 4
            r = 2
        elif self.target == "beats":
            f = 2
            r = 2
        elif self.target == "bars":
            f = 1
            r = 1
        for k in xrange(0, r):
            for i in xrange(0, 4*f):
                onebar.append( s1[i % len(s1)] )
            for i in xrange(4*f, 6*f):
                onebar.append(  s2[i % len(s2)]  )
            for i in xrange(6*f, 8*f):
                onebar.append(  s3[i % len(s3)]  )
        if self.original.analysis.time_signature == 4:
            orig_bar = self.st.shiftTempo( audio.getpieces( self.original, onebar ), self.template['tempo']/self.tempo )
        else:
            orig_bar = audio.getpieces( self.original, onebar )
            orig_bar = self.st.shiftTempo( orig_bar, len( orig_bar ) / ( ( 44100 * 16 * 2 * 60.0 )/self.template['tempo'] ) )
        if orig_bar.numChannels == 1:
            orig_bar = self.mono_to_stereo( orig_bar )
        mixfactor = self.mixfactor( onebar )
        a = self.truncatemix(
                audio.mix(
                    audio.AudioData(
                        self.template['wubs'][self.tonic], 
                        sampleRate=44100,
                        numChannels=2,
                        verbose=False
                    ),
                    audio.AudioData(
                        self.template['splashes'][(j+1) % len( self.template['splashes'] )],
                        sampleRate=44100,
                        numChannels=2,
                        verbose=False
                    )
                ),
            orig_bar,
            mixfactor
        )
        b = self.truncatemix(
                audio.mix(
                    audio.AudioData(
                        self.template['wub_breaks'][self.tonic],
                        sampleRate=44100,
                        numChannels=2,
                        verbose=False
                    ),
                    hats
                ),
            orig_bar,
            mixfactor
        )
        return (a, b)

    def updateTags( self, text=u" (Wub Machine Remix)" ):
        """
            Updates the MP3 tags after remixing is complete.
            Can use a mutagen tag (mt) from an MP3 or an M4A.
            Also uses PIL to overlay the WubMachine decal on the cover art.
            The resulting art is saved (for SoundCloud), thumbnailed
            (for the web frontend), and embedded into the new MP3.
        """
        if not self.mt:
            return
        try:
            if 'title' in self.tag:
                self.tag['new_title'] = self.tag['title'] + text 
            else:
                self.tag['new_title'] = "[untitled] %s" % text

            if 'TIT2' in self.mt:
                self.mt['TIT2'].text[0] += text
            elif '\xa9nam' in self.mt:
                self.mt['\xa9nam'][0] += text

            outtag = File( self.outfile )  
            outtag.add_tags()
            outtag.tags.add( id3.TBPM( encoding=0, text=unicode( self.template['tempo'] ) ) )
            if self.extension == ".mp3":
                for k, v in self.mt.iteritems():
                    if k != 'APIC:':
                        outtag.tags.add( v )
                if "APIC:" in self.mt:
                    imgmime = self.mt['APIC:'].mime
                    imgdata = self.mt['APIC:'].data
            elif self.extension == ".m4a":
                tags = {
                    '\xa9alb': id3.TALB,
                    '\xa9ART': id3.TPE1,
                    '\xa9nam': id3.TIT2,
                    '\xa9gen': id3.TCON                    
                }
                for k, v in self.mt.iteritems():
                    if k in tags:
                        outtag.tags.add( tags[ k ]( encoding=0, text=v[0] ) )
                if 'trkn' in self.mt:
                    if type( self.mt['trkn'][0] == tuple ):
                        outtag.tags.add( id3.TRCK( encoding=0, text=( "%s/%s" % ( self.mt['trkn'][0][0], self.mt['trkn'][0][1] ) ) ) )
                    else:
                        outtag.tags.add( id3.TRCK( encoding=0, text=( self.mt['trkn'][0] ) ) )
                if 'disk' in self.mt:
                    if type( self.mt['disk'][0] == tuple ):
                        outtag.tags.add( id3.TPOS( encoding=0, text=( "%s/%s" % ( self.mt['disk'][0][0], self.mt['disk'][0][1] ) ) ) )
                    else:
                        outtag.tags.add( id3.TPOS( encoding=0, text=( self.mt['disk'][0] ) ) )              
                if "covr" in self.mt:
                    if self.mt['covr'][0][0:4] == '\x89PNG':
                        imgmime = u'image/png'
                    elif self.mt['covr'][0][0:10] == '\xff\xd8\xff\xe0\x00\x10JFIF':
                        imgmime = u'image/jpeg'
                    imgdata = self.mt['covr'][0]
            if imgdata:
                if imgmime == u"image/jpeg":
                    artname = "uploads/%s.jpg" % self.uid
                    outname = "static/songs/%s.jpg" % self.uid
                elif imgmime == u"image/png":
                    artname = "uploads/%s.png" % self.uid
                    outname = "static/songs/%s.png" % self.uid
                else:
                    raise Exception( "Unknown artwork format!")
                thumbname = "static/songs/%s.thumb.jpg" % self.uid

                artwork = open( artname, "w" )
                artwork.write( imgdata )
                artwork.close()

                overlay = Image.open( 'static/img/overlay.png' )
                artwork = Image.open( artname ).resize( (500, 500), Image.BICUBIC )
                artwork.paste( overlay, None, overlay )

                artwork.save( outname )
                artwork.resize( (80, 80), Image.ANTIALIAS ).convert( "RGB" ).save( thumbname )

                unlink( artname )

                outtag.tags.add(
                    id3.APIC(
                        encoding=3, # 3 is for utf-8
                        mime=imgmime, # image/jpeg or image/png
                        type=3, # 3 is for the cover image
                        desc=u'Cover',
                        data=open( outname ).read()
                    )
                )
                self.tag["art"] = outname
                self.tag["thumbnail"] = thumbname
                self.tag["remixed"] = 'static/songs/%s.mp3' % self.uid
            outtag.save()
        except:
            pass

    def remix( self ):
        """
            Wub wub wub wub wub wub wub wub wub wub wub wub wub wub wub wub wub wub.
        """
        try:
            self.log( "Fetching metadata...", 5 )
            self.getTag()

            self.log( "Listening to %s..." % ( '"%s"' % self.tag['title'] if 'title' in self.tag else 'song' ), 5 )
            self.original = audio.LocalAudioFile( self.infile, False )
            if self.deleteOriginal:
                unlink( self.infile )
            self.st = FastModify()
            
            self.log( "Choosing key and tempo...", 10 )
            self.tonic = self.original.analysis.key['value']
            self.tempo = self.original.analysis.tempo['value']
            self.bars = self.original.analysis.bars
            self.beats = self.original.analysis.beats
            self.sections = self.original.analysis.sections
            self.tag[ 'key' ] = self.keys[ self.tonic ]
            self.tag[ 'tempo' ] = self.template[ 'tempo' ]

            if not len( self.sections ):
                raise Exception( "This doesn't look like music!" )

            self.log( "Arranging intro...", 40.0/( len( self.sections ) + 1 ) )
            self.partialEncode( self.compileIntro() )

            past_progress = 0
            hats  = audio.AudioData( self.template['hats'], sampleRate=44100, numChannels=2, verbose=False )
            for i, section in enumerate( self.sections ):
                self.log( "Arranging section %s of %s..." % ( i+1, len( self.sections ) ), 40.0/( len( self.sections ) + 1 ) )
                a, b = self.compileSection( i, section, hats )
                self.partialEncode( a )
                self.partialEncode( b )
                del a, b
            del hats
            self.original.unload()

            self.log( "Adding ending...", 5 )
            self.partialEncode(
                audio.AudioData(
                    self.template['splash_ends'][( i + 1 ) % len( self.template['splash_ends'] )],
                    sampleRate=44100,
                    numChannels=2,
                    verbose=False
                )
            )
            
            self.log( "Mixing...", 5 )
            self.mixwav( self.tempfile )

            self.log( "Mastering...", 5 )
            self.lame( self.tempfile, self.outfile )
            unlink( self.tempfile )
            
            self.log( "Adding artwork...", 20 )
            self.updateTags()
            
            self.finish( "Done!" )
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print_exception(exc_type, exc_value, exc_traceback,limit=2, file=sys.stderr)
            self.error( format_exc().splitlines()[-1] )
        finally:
            self.cleanup()

if __name__ == "__main__":
    CMDRemix( Dubstep )
