#!/usr/bin/env python
"""
drums.py

Add drums to a song.

At the moment, only works with songs in 4, and endings are rough.

By Ben Lacker, 2009-02-24.
"""
import numpy
import sys
import time

import echonest.audio as audio
from echonest import modify
from echonest.selection import *
from echonest.sorting import *

from pprint import pprint

usage="""
Usage:
    python drums.py <inputfilename> <breakfilename> <outputfilename> <beatsinbreak> <barsinbreak> [<drumintensity>]

Example:
    python drums.py HereComesTheSun.mp3 breaks/AmenBrother.mp3 HereComeTheDrums.mp3 64 4 0.6

Drum instenity defaults to 0.5
"""

keys = {0: "C", 1: "C#", 2: "D", 3: "Eb", 4: "E", 5:"F", 6:"F#", 7:"G", 8:"G#", 9:"A", 10:"Bb", 11:"B"}
scale = []

def main(input_filename, output_filename):
    st = modify.Modify()
    audiofile = audio.LocalAudioFile(input_filename)
    tonic = audiofile.analysis.key['value']
    tempo = audiofile.analysis.tempo['value']

    pprint(tempo);


    print "The tonic of this song is %s." % keys[tonic]

    acceptable_sample_pitches = [tonic, (tonic + 5) % 12, (tonic + 7) % 12]
    print "Acceptable pitches of samples that will be used: %s, %s and %s." % (keys[acceptable_sample_pitches[0]], keys[acceptable_sample_pitches[1]], keys[acceptable_sample_pitches[2]])

   # fade_in = audiofile.analysis.end_of_fade_in
   # fade_out = audiofile.analysis.start_of_fade_out

    bars = audiofile.analysis.bars#.that(are_contained_by_range(fade_in, fade_out))
    beats = audiofile.analysis.beats#.that(are_contained_by_range(fade_in, fade_out))	

    samples = {}
    for pitch in acceptable_sample_pitches:
        samples[pitch] = beats.that(overlap_ends_of(audiofile.analysis.segments.that(have_pitch_max(pitch)).that(overlap_starts_of(beats))))

#    i=0
#    for pitch, pitchsamples in samples.iteritems():
#        for s in pitchsamples:
#        #    s.encode("%s_%s_%s.mp3" % (output_filename, keys[pitch], i))
#            i += 1

    audioout = audio.AudioData(shape= (len(audiofile)+100000,2), sampleRate=44100, numChannels=2)
    out = audio.AudioQuantumList()

    """
    We could use bars here, but unfortunately, the beat detection is more reliable than the bar detection.
    Hence, we create our own bars of 4.
    """

    """
        SONG INTRO SECTION
        Plays first four bars of song like usual.
        Then loops:
            first quarter note of first bar         x 4
            first quarter note of second bar        x 4
            first eighth note of third bar          x 8
            first sixteenth note of fourth bar      x 8
            third sixteenth note of fourth bar      x 8
    """


#    for i, s in enumerate(audiofile.analysis.bars):
#        audio.getpieces(audiofile, [s]).encode("bar_%s_%s" % (i, output_filename))

    low        = audio.AudioData('samples/sub_long01.wav', sampleRate=44100, numChannels=2)

    custom_bars = []
    audioout.append(audio.mix(audiofile.__getitem__(beats[0]), low))

    custom_bars.append(beats[1:3])
    custom_bars.append(beats[4:8])
    custom_bars.append(beats[8:12])
    custom_bars.append(beats[12:16])    

    out.extend([x for bar in custom_bars for x in bar])
    
    out.append(custom_bars[0][0])
    out.append(custom_bars[0][0])
    out.append(custom_bars[0][0])
    out.append(custom_bars[0][0])
    
    out.append(custom_bars[1][0])
    out.append(custom_bars[1][0])
    out.append(custom_bars[1][0])
    out.append(custom_bars[1][0])


    beatone = custom_bars[2][0]
    beattwo = custom_bars[3][0]
    beatthree = custom_bars[3][2]
    
    for x in range(0, 8):
        out.append(audio.AudioQuantum(beatone.start, beatone.duration/2, None, beatone.confidence, beatone.source))
    for x in range(0, 8):
        out.append(audio.AudioQuantum(beattwo.start, beattwo.duration/4, None, beattwo.confidence, beattwo.source))
    for x in range(0, 8):
        out.append(audio.AudioQuantum(beatthree.start, beatthree.duration/4, None, beatthree.confidence, beatthree.source))
    
    audioout.append(audio.getpieces(audiofile, out))

    st.shiftTempo(audioout, 140/tempo).encode("%s.mp3" % output_filename)

if __name__=='__main__':
    try:
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]
    except:
        print usage
        sys.exit(-1)
    main(input_filename, output_filename)

