"""
Dependencies:
    Remixer
    lame (command line binary)
"""

from remixer import *
from echonest.selection import *
from echonest.sorting import *
import math
import numpy

def avg(xArr):
    return round(float(sum(xArr)/len(xArr)),1)

def stddev(xArr):
    return "std"

def are_kicks(x):
    bright = x.timbre[1] < 20
    #flat =  x.timbre[2] < 0 
    attack = x.timbre[3] > 80
    return bright

def are_snares(x):
    loud = x.timbre[0] > 10
    bright = x.timbre[1] > 100 and x.timbre[1] < 150
    flat =  x.timbre[2] < 30
    attack = x.timbre[3] > 20
    return loud and bright and flat and attack

def are_hats(x):
    loud = x.timbre[0] < 45
    bright = x.timbre[1] > 90
    flat =  x.timbre[2] < 0
    attack = x.timbre[3] > 70
    what = x.timbre[4] < 40
    return loud and bright and flat and attack and what

class Beatbox(Remixer):
    template = {
      'hats': 'hat.wav',
      'kick': 'kick.wav',
      'snare': 'snare.wav'
        }

    def remix(self):
        """
            Remixing happens here. Take your input file from self.infile and write your remix to self.outfile.
            If necessary, self.tempfile can be used for temp files. 
        """
        self.original = audio.LocalAudioFile(self.infile)
        #for i, segment in enumerate(self.original.analysis.segments):
        #    segment.encode("seg_%s.mp3" % i)
        print "\n\n\n"
        loudnesses = [x.timbre[0] for i, x in enumerate(self.original.analysis.segments)]
        brightnesses = [x.timbre[1] for i, x in enumerate(self.original.analysis.segments)]
        flatnesses = [x.timbre[2] for i, x in enumerate(self.original.analysis.segments)]
        attacks = [x.timbre[3] for i, x in enumerate(self.original.analysis.segments)]
        timbre5 = [x.timbre[4] for i, x in enumerate(self.original.analysis.segments)]
        timbre6 = [x.timbre[5] for i, x in enumerate(self.original.analysis.segments)]
        timbre7 = [x.timbre[6] for i, x in enumerate(self.original.analysis.segments)]
        timbre8 = [x.timbre[7] for i, x in enumerate(self.original.analysis.segments)]
        timbre9 = [x.timbre[8] for i, x in enumerate(self.original.analysis.segments)]
        timbre10 = [x.timbre[9] for i, x in enumerate(self.original.analysis.segments)]
        timbre11 = [x.timbre[10] for i, x in enumerate(self.original.analysis.segments)]
        timbre12 = [x.timbre[11] for i, x in enumerate(self.original.analysis.segments)]

        print "AVERAGES"
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % ('loud','bright','flat','attack','t5','t6','t7','t8','t9','t10','t11','t12')
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % (avg(loudnesses),avg(brightnesses),avg(flatnesses),avg(attacks),avg(timbre5),avg(timbre6),avg(timbre7),avg(timbre8),avg(timbre9),avg(timbre10),avg(timbre11),avg(timbre12))
        print
        print "STDVS"
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % ('loud','bright','flat','attack','t5','t6','t7','t8','t9','t10','t11','t12')
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % (stddev(loudnesses),stddev(brightnesses),stddev(flatnesses),stddev(attacks),stddev(timbre5),stddev(timbre6),stddev(timbre7),stddev(timbre8),stddev(timbre9),stddev(timbre10),stddev(timbre11),stddev(timbre12))


        print "\tLoud\tBright\tFlat\tAttack\ttim5\ttim6\ttim7\ttim8\ttim9\ttim10\ttim11\ttim12"
        for segment in self.original.analysis.segments:
            if are_kicks(segment): print "Kick",
            elif are_snares(segment): print "Snar",
            elif are_hats(segment): print "Hats",
            else: print "else",
            print "\t%s\t%s\t%s\t%s\t%s" % (segment.timbre[0], segment.timbre[1], segment.timbre[2], segment.timbre[3], segment.timbre[4])

        kicks = self.original.analysis.segments.that(are_kicks)
        #if kicks: kicks.encode('kicks.mp3')
        snares = self.original.analysis.segments.that(are_snares)
        #if snares: snares.encode('snares.mp3')
        hats = self.original.analysis.segments.that(are_hats)
        #if hats: hats.encode('hats.mp3')

        # Time to replace
        hat_sample = audio.AudioData(self.sample_path + self.template['hats'], sampleRate=44100, numChannels=2, verbose=False)
        kick_sample = audio.AudioData(self.sample_path + self.template['kick'], sampleRate=44100, numChannels=2, verbose=False)
        snare_sample = audio.AudioData(self.sample_path + self.template['snare'], sampleRate=44100, numChannels=2, verbose=False)
  
        empty = audio.AudioData(ndarray=numpy.zeros(((self.original.sampleRate * self.original.analysis.duration), 2), dtype=numpy.int16), numChannels=2, sampleRate=44100)

        last = 0
        for segment in kicks:
            if last + len(kick_sample.data) > segment.start:
                print "Adding kick at %s" % segment.start
                empty.data[self.original.sampleRate*segment.start:self.original.sampleRate*segment.start + len(kick_sample.data)] += kick_sample.data
            last = segment.start

        last = 0
        for segment in snares:
            if last + len(snare_sample.data) > segment.start:
                print "Adding snare at %s" % segment.start
                empty.data[self.original.sampleRate*segment.start:self.original.sampleRate*segment.start + len(snare_sample.data)] += snare_sample.data     
            last = segment.start
        for segment in hats:
            if last + len(hat_sample.data) > segment.start:
                print "Adding hat at %s" % segment.start
                empty.data[self.original.sampleRate*segment.start:self.original.sampleRate*segment.start + len(hat_sample.data)] += hat_sample.data
            last  = segment.start

        audio.mix(empty, self.original, 0.5).encode('mixed.mp3')

if __name__ == "__main__":
    CMDRemix(Beatbox)

