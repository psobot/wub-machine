"""
dubstep.py <ex: dubstepize.py, wubmachine.py, wubwub.py, etc...>

Turns a song into a dubstep remix.
ElectroHouse inherits from the Remixer class.
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

from remixer import *
from helpers.fastmodify import FastModify
from echonest.modify import Modify
from echonest.action import make_stereo
import numpy

tempo = 128.0

# Audio Division
def half_of(audioData):
    return divide(audioData, 2)[0]

def third_of(audioData):
    return divide(audioData, 3)[0]

def quarter_of(audioData):
    return divide(audioData, 4)[0]

def eighth_of(audioData):
    return divide(audioData, 8)[0]

def eighth_triplet(audioData):
    return cutnote(audioData, 6)

def quarter_triplet(audioData):
    return cutnote(audioData, 3)

def sixteenth_note(audioData):
    return cutnote(audioData, 4)

def eighth_note(audioData):
    return cutnote(audioData, 2)

def dotted_eighth_note(audioData):
    return cutnote(audioData, 0.75)

def quarter_note(audioData):
    return cutnote(audioData, 1)
    
def cutnote(audioData, length):
    beatlength = (audioData.sampleRate * 60 / tempo) #in samples
    i = beatlength/length
    data = audioData.data[0:i]
    if len(data) < i:
        if audioData.numChannels == 2:
            shape = (i - len(data),2)
        else:
            shape = (i - len(data),)
        data = numpy.append(data, numpy.zeros(shape, dtype=numpy.int16), 0)
    r = audio.AudioData(
        ndarray=data,
        numChannels=audioData.numChannels,
        sampleRate = audioData.sampleRate
    )
    return make_stereo(r) if (r.numChannels == 1) else r

def divide(audioData, by):
    return [audio.AudioData(
        ndarray=audioData.data[i:len(audioData.data)/by],
        numChannels=audioData.numChannels,
        sampleRate = audioData.sampleRate
    ) for i in xrange(0, len(audioData.data), len(audioData.data)/by)]

quarter_rest = audio.AudioData(ndarray=numpy.zeros(         ((44100 * 60 / tempo), 2),      dtype=numpy.int16), numChannels=2, sampleRate=44100)
eighth_rest = audio.AudioData(ndarray=numpy.zeros(          ((44100 * 60 / tempo)/2, 2),    dtype=numpy.int16), numChannels=2, sampleRate=44100)
dotted_eighth_rest = audio.AudioData(ndarray=numpy.zeros(   ((44100 * 60 / tempo)/0.75, 2), dtype=numpy.int16), numChannels=2, sampleRate=44100)
quarter_triplet_rest = audio.AudioData(ndarray=numpy.zeros( ((44100 * 60 / tempo)/3, 2),    dtype=numpy.int16), numChannels=2, sampleRate=44100)
sixteenth_rest = audio.AudioData(ndarray=numpy.zeros(       ((44100 * 60 / tempo)/4, 2),    dtype=numpy.int16), numChannels=2, sampleRate=44100)

rhythm_map = {1: sixteenth_note, 2: eighth_note, 3: dotted_eighth_note, 4: quarter_note}
rest_map = {1: sixteenth_rest, 2: eighth_rest, 3: dotted_eighth_rest, 4: quarter_rest}

class note():
  def __init__(self, pitch=None, length=1):
        self.pitch = pitch
        self.length = length
        self.data = rest_map[length]
        self.function = rhythm_map[length]
  def __repr__(self):
        return "%s x 16th note %s" % (self.length, self.pitch if self.pitch is not None else "rest")

def readPattern(filename):
    f = open(filename)
    f.readline()
    # Two spaces for each beat.
    # number 1 through 12 means that note (rather, that interval from root)
    # dash means continue previous
    pattern = []
    for s in f:
        if "+" in s or '#' in s or s == "\n":
            continue
        pattern.extend([''.join(x) for x in zip(*[list(s[z::2]) for z in xrange(2)])])

    bar = [] 
    for sixteenth in pattern:
        if sixteenth == "" or sixteenth == " \n":
            continue
        elif sixteenth == "  ":
            bar.append(note())
        elif sixteenth == "- ":
            last = bar.pop()
            bar.append(note(last.pitch, last.length+1))
        else:
            bar.append(note(int(sixteenth)))
    return bar

class ElectroHouse(Remixer):
    template = {
        'tempo':        128,
        'beat':        ['beat_%s.wav' % i for i in xrange(0, 4)],
        'intro': 'intro_16.wav',
        'splash':     'splash.wav',
        'build':      'build.wav',
        'body' : [
          'body/c.wav',
          'body/c-sharp.wav',
          'body/d.wav',
          'body/d-sharp.wav',
          'body/e.wav',
          'body/f.wav',
          'body/f-sharp.wav',
          'body/g.wav',
          'body/g-sharp.wav',
          'body/a.wav',
          'body/a-sharp.wav',
          'body/b.wav'
        ],
        'mixpoint': 18,     # "db factor" of wubs - 0 is softest wubs, infinity is... probably extremely loud 
        'target': "beats",
        'splash_ends':  [  'splash-ends/1.wav',
                            'splash-ends/2.wav',
                            'splash-ends/3.wav',
                            'splash-ends/4.wav'
                        ],
    }
    st = None
    sampleCache = {}

    def searchSamples(self, j, key):
        """
            Find all samples (beats) of a given key in a given section.
        """
        hashkey = "_%s-%s" % (j, key)
        if not hashkey in self.sampleCache:
            if self.sections:
                pool = self.sections[j % len(self.sections)]
            elif self.original.analysis.bars:
                pool = self.original.analysis.bars
            elif self.original.analysis.segments:
                pool = self.original.analysis.segments
            else:
                raise Exception("No samples found for section %s." % j+1)
            a = self.getSamples(pool, key)
            for tries in xrange(0, 5):
                if len(a):
                    break
                key = (key + 7) % 12
                a = self.getSamples(pool, key)
            else:
                for tries in xrange(0, 5):
                    if len(a):
                        break
                    if self.sections:
                        j = (j + 1) % len(self.sections)
                    elif self.original.analysis.bars:
                        j = (j + 1) % len(self.original.analysis.bars)
                    elif self.original.analysis.segments:
                        j = (j + 1) % len(self.original.analysis.segments)
                    key = (key + 2) % 12
                    a = self.getSamples(pool, key)
            self.sampleCache[hashkey] = a
        return self.sampleCache[hashkey]

    def getSamples(self, section, pitch, target="beats"):
        """
            The EchoNest-y workhorse. Finds all beats/bars in a given section, of a given pitch.
        """
        hashkey = "__%s.%s" % (str(section), pitch)
        if not hashkey in self.sampleCache:
            sample_list = audio.AudioQuantumList()
            if target == "beats":
                try:
                    sample_list.extend([b for x in section.children() for b in x.children()])
                except:
                    sample_list.extend(section)
            elif target == "bars":
                sample_list.extend(section.children())
            self.sampleCache[hashkey] = sample_list.that(overlap_ends_of(self.original.analysis.segments.that(have_pitch_max(pitch)).that(overlap_starts_of(sample_list))))
        return self.sampleCache[hashkey]

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

    def compileIntro(self, section=0, intro=None):
        if not intro:
            intro = audio.AudioData(self.sample_path + self.template['intro'], sampleRate=44100, numChannels=2, verbose=False)
        out = audio.AudioQuantumList()
        section_hash_keys = []

        for i, item in enumerate(readPattern('samples/electrohouse/intro.txt')):
            if item.pitch is None:
                out.append(item.data)
            else:
                samples = self.searchSamples(section, (item.pitch + self.tonic) % 12) 
                if not samples:
                    out.append(item.data)
                else:
                    hash_key = str(samples[i%len(samples)])
                    if not hash_key in self.sampleCache:
                        self.sampleCache[hash_key] = self.st.shiftTempo(samples[i%len(samples)].render(), self.template['tempo']/self.tempo)
                        section_hash_keys.append(hash_key)
                    out.append(
                      item.function(
                        self.sampleCache[hash_key]
                      )
                    )
        shifted = audio.assemble(out, numChannels = 2)
        if shifted.numChannels == 1:    
            shifted = self.mono_to_stereo(shifted)
        for hash_key in section_hash_keys:
            del self.sampleCache[hash_key]
        return self.truncatemix(intro, shifted, 0.3)

    def compileSection(self, j, section, backing):
        out = audio.AudioQuantumList()
        section_hash_keys = []

        for i, item in enumerate(readPattern('samples/electrohouse/section.txt')):
            if item.pitch is None:
                out.append(item.data)
            else:
                samples = self.searchSamples(j, (item.pitch + self.tonic) % 12)
                if not samples:
                    out.append(item.data)
                else:
                    hash_key = str(samples[i%len(samples)])
                    if not hash_key in self.sampleCache:
                        self.sampleCache[hash_key] = self.st.shiftTempo(samples[i%len(samples)].render(), self.template['tempo']/self.tempo)
                        section_hash_keys.append(hash_key)
                    out.append(
                      item.function(
                          self.sampleCache[hash_key]
                      )
                    )
        shifted = audio.assemble(out, numChannels = 2)
        if shifted.numChannels == 1:
            shifted = self.mono_to_stereo(shifted)
        for hash_key in section_hash_keys:
            del self.sampleCache[hash_key]
        return self.truncatemix(backing, shifted, 0.3)

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
        if not self.tempo:
            self.tempo = 128.0
        self.bars = self.original.analysis.bars
        self.beats = self.original.analysis.beats
        self.sections = self.original.analysis.sections
        self.tag['key'] = self.keys[self.tonic] if self.tonic >= 0 and self.tonic < 12 else '?'
        if 'title' in self.tag and self.tag['title'] == u'I Wish':
            self.tonic += 2
            self.tag['key'] = 'D#'
        self.tag['tempo'] = self.template['tempo']

        self.log("Arranging intro...", 40.0/(len(self.sections) + 1))
        intro = audio.AudioData(self.sample_path + self.template['intro'], sampleRate=44100, numChannels=2, verbose=False)
        self.partialEncode(self.compileIntro(0, intro))

        i = 0 # Required if there are no sections
        sections = self.sections[1:] if len(self.sections) % 2 else self.sections
        if len(sections) > 2:
            backing = audio.AudioData(self.sample_path + self.template['body'][self.tonic], sampleRate=44100, numChannels=2, verbose=False)
            for i, section in enumerate(sections):
                self.log("Arranging section %s of %s..." % (i+1, len(sections)), 40.0/(len(sections) + 1))
                a = self.compileSection(i, section, backing) if i != (len(sections)/2 + 1) else self.compileIntro(i, intro)
                self.partialEncode(a)
                del a
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
        self.updateTags(titleSuffix = " (Wub Machine Electro Remix)")
        
        return self.outfile

if __name__ == "__main__":
    CMDRemix(ElectroHouse)

