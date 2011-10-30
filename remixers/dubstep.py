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
based off of code by Ben Lacker, 2009-02-24.
"""

from remixer import Remixer, CMDRemix
from helpers.fastmodify import FastModify

from os import unlink
from echonest.selection import *
from echonest.sorting import *
import echonest.audio as audio

class Dubstep(Remixer):
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
        'intro':        'intro-eight.wav',
        'hats':         'hats.wav',
        'wubs':         [  'wubs/c.wav',
                            'wubs/c-sharp.wav',
                            'wubs/d.wav',
                            'wubs/d-sharp.wav',
                            'wubs/e.wav',
                            'wubs/f.wav',
                            'wubs/f-sharp.wav',
                            'wubs/g.wav',
                            'wubs/g-sharp.wav',
                            'wubs/a.wav',
                            'wubs/a-sharp.wav',
                            'wubs/b.wav'
                        ],
        'wub_breaks':   [  'break-ends/c.wav',
                            'break-ends/c-sharp.wav',
                            'break-ends/d.wav',
                            'break-ends/d-sharp.wav',
                            'break-ends/e.wav',
                            'break-ends/f.wav',
                            'break-ends/f-sharp.wav',
                            'break-ends/g.wav',
                            'break-ends/g-sharp.wav',
                            'break-ends/a.wav',
                            'break-ends/a-sharp.wav',
                            'break-ends/b.wav'
                        ],
        'splashes':     [  'splashes/splash_03.wav',
                            'splashes/splash_04.wav',
                            'splashes/splash_02.wav',
                            'splashes/splash_01.wav',
                            'splashes/splash_05.wav',
                            'splashes/splash_07.wav',
                            'splashes/splash_06.wav',
                            'splashes/splash_08.wav',
                            'splashes/splash_10.wav',
                            'splashes/splash_09.wav',
                            'splashes/splash_11.wav'
                        ],
        'splash_ends':  [  'splash-ends/1.wav',
                            'splash-ends/2.wav',
                            'splash-ends/3.wav',
                            'splash-ends/4.wav'
                        ],
        'mixpoint': 18,     # "db factor" of wubs - 0 is softest wubs, infinity is... probably extremely loud 
        'target': "beats"
    }
    st = None

    def searchSamples(self, j, key):
        """
            Find all samples (beats) of a given key in a given section.
        """
        a = self.getSamples(self.sections[j], key)
        for tries in xrange(0, 5):
            if len(a):
                break
            key = (key + 7) % 12
            a = self.getSamples(self.sections[j], key)
        else:
            for tries in xrange(0, 5):
                if len(a):
                    break
                j = (j + 1) % len(self.sections)
                key = (key + 2) % 12
                a = self.getSamples(self.sections[j], key)
        return a

    def getSamples(self, section, pitch, target="beats"):
        """
            The EchoNest-y workhorse. Finds all beats/bars in a given section, of a given pitch.
        """
        sample_list = audio.AudioQuantumList()
        if target == "beats":
            sample_list.extend([b for x in section.children() for b in x.children()]);
        elif target == "bars":
            sample_list.extend(section.children())
        return sample_list.that(overlap_ends_of(self.original.analysis.segments.that(have_pitch_max(pitch)).that(overlap_starts_of(sample_list))))

    def mixfactor(self, segment):
        """
            Computes a rough "mixfactor" - the balance between wubs and original audio for a given segment.
            Mixfactor returned:
              1: full wub
              0: full original
            Result can be fed into echonest.audio.mix() as the third parameter.
        """
        mixfactor = 0
        a = (89.0/1.5) + self.template['mixpoint']
        b = (188.0/1.5) + self.template['mixpoint']
        loud = self.loudness(self.original.analysis.segments, segment)
        if not loud:
            loud = self.original.analysis.loudness
        if loud != -1 * b:
            mixfactor = float(float(loud + a)/float(loud + b))
        if mixfactor > 0.8:
            mixfactor = 0.8
        elif mixfactor < 0.3:
            mixfactor = 0.3
        return mixfactor

    def compileIntro(self):
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
        intro = audio.AudioData(self.sample_path + self.template['intro'], sampleRate=44100, numChannels=2, verbose=False)
        
        #   First 4 bars of song
        custom_bars = []

        if not self.beats or len(self.beats) < 16:
            #   Song is not long or identifiable enough
            #   Take our best shot at making something
            self.tempo = 60.0 * 16.0 / self.original.duration
            for i in xrange(0, 4):
                bar = []
                for j in xrange(0, 4):
                    length = self.original.duration / 16.0
                    start = ((i * 4) + j) * length
                    bar.append(audio.AudioQuantum(start, length, None, 0, self.original.source))
                custom_bars.append(bar)
        else:
            for i in xrange(0, 4):
                custom_bars.append(self.beats[i*4:(i*4)+4])
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
            out.append(audio.AudioQuantum(beatone.start, beatone.duration/2, None, beatone.confidence, beatone.source))

        #   First beat of fourth bar x 8
        for x in xrange(0, 8):
            out.append(audio.AudioQuantum(beattwo.start, beattwo.duration/4, None, beattwo.confidence, beattwo.source))

        #   Third beat of fourth bar x 8
        for x in xrange(0, 8):
            out.append(audio.AudioQuantum(beatthree.start, beatthree.duration/4, None, beatthree.confidence, beatthree.source))
        
        if self.original.analysis.time_signature == 4:
            shifted = self.st.shiftTempo(audio.getpieces(self.original, out), self.template['tempo']/self.tempo)
        else:
            shifted1 = audio.getpieces(self.original, out)
            shifted = self.st.shiftTempo(shifted1, len(shifted1) / ((44100 * 16 * 2 * 60.0)/self.template['tempo']))
            shifted1.unload()
        if shifted.numChannels == 1:    
            shifted = self.mono_to_stereo(shifted)
        return self.truncatemix(intro, shifted, self.mixfactor(out))

    def compileSection(self, j, section, hats):
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

        s1 = self.searchSamples(j, self.tonic)
        s2 = self.searchSamples(j, (self.tonic + 3) % 12)
        s3 = self.searchSamples(j, (self.tonic + 9) % 12)

        biggest = max([s1, s2, s3]) #for music that's barely tonal
        if not biggest:
            for i in xrange(0, 12):
                biggest = self.searchSamples(j, self.tonic + i)
                if biggest:
                    break

        if not biggest:
            raise Exception('Missing samples in section %s of the song!' % j+1)

        if not s1: s1 = biggest
        if not s2: s2 = biggest
        if not s3: s3 = biggest

        if self.template['target'] == "tatums":
            f = 4
            r = 2
        elif self.template['target'] == "beats":
            f = 2
            r = 2
        elif self.template['target'] == "bars":
            f = 1
            r = 1
        for k in xrange(0, r):
            for i in xrange(0, 4*f):
                onebar.append(s1[i % len(s1)])
            for i in xrange(4*f, 6*f):
                onebar.append( s2[i % len(s2)] )
            for i in xrange(6*f, 8*f):
                onebar.append( s3[i % len(s3)] )
        if self.original.analysis.time_signature == 4:
            orig_bar = self.st.shiftTempo(audio.getpieces(self.original, onebar), self.template['tempo']/self.tempo)
        else:
            orig_bar = audio.getpieces(self.original, onebar)
            orig_bar = self.st.shiftTempo(orig_bar, len(orig_bar) / ((44100 * 16 * 2 * 60.0)/self.template['tempo']))
        if orig_bar.numChannels == 1:
            orig_bar = self.mono_to_stereo(orig_bar)
        mixfactor = self.mixfactor(onebar)
        a = self.truncatemix(
                audio.mix(
                    audio.AudioData(
                        self.sample_path + self.template['wubs'][self.tonic], 
                        sampleRate=44100,
                        numChannels=2,
                        verbose=False
                    ),
                    audio.AudioData(
                        self.sample_path + self.template['splashes'][(j+1) % len(self.template['splashes'])],
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
                        self.sample_path + self.template['wub_breaks'][self.tonic],
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

    def remix(self):
        """
            Wub wub wub wub wub wub wub wub wub wub wub wub wub wub wub wub wub wub.
        """
        self.log("Looking up track...", 5)
        self.getTag()
        self.processArt()

        self.log("Listening to %s..." % ('"%s"' % self.tag['title'] if 'title' in self.tag else 'song'), 5)
        self.original = audio.LocalAudioFile(self.infile, False)
        if not 'title' in self.tag:
            self.detectSong(self.original)
        self.st = FastModify()
        
        self.log("Choosing key and tempo...", 10)
        self.tonic = self.original.analysis.key['value']
        self.tempo = self.original.analysis.tempo['value']
        self.bars = self.original.analysis.bars
        self.beats = self.original.analysis.beats
        self.sections = self.original.analysis.sections
        self.tag['key'] = self.keys[self.tonic] if self.tonic >= 0 and self.tonic < 12 else '?'
        self.tag['tempo'] = self.template['tempo']

        self.log("Arranging intro...", 40.0/(len(self.sections) + 1))
        self.partialEncode(self.compileIntro())

        past_progress = 0
        hats  = audio.AudioData(self.sample_path + self.template['hats'], sampleRate=44100, numChannels=2, verbose=False)

        i = 0 # Required if there are no sections
        for i, section in enumerate(self.sections):
            self.log("Arranging section %s of %s..." % (i+1, len(self.sections)), 40.0/(len(self.sections) + 1))
            a, b = self.compileSection(i, section, hats)
            self.partialEncode(a)
            self.partialEncode(b)
            del a, b
        del hats
        self.original.unload()

        self.log("Adding ending...", 5)
        self.partialEncode(
            audio.AudioData(
                self.sample_path + self.template['splash_ends'][(i + 1) % len(self.template['splash_ends'])],
                sampleRate=44100,
                numChannels=2,
                verbose=False
            )
        )
        
        self.log("Mixing...", 5)
        self.mixwav(self.tempfile)

        if self.deleteOriginal:
            try:
                unlink(self.infile)
            except:
                pass  # File could have been deleted by an eager cleanup script

        self.log("Mastering...", 5)
        self.lame(self.tempfile, self.outfile)
        unlink(self.tempfile)
        
        self.log("Adding artwork...", 20)
        self.updateTags(titleSuffix = " (Wub Machine Remix)")
        
        return self.outfile

if __name__ == "__main__":
    CMDRemix(Dubstep)
