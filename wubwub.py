#!/usr/bin/env python
"""
dubstepize.py

Turns a song into a dubstep remix.

by Peter Sobot <hi@petersobot.com>, started Jan. 2011
based off of code by Ben Lacker, 2009-02-24.
"""
import numpy
import sys
import time
import os
import math

import echonest.audio as audio
from echonest import modify
from echonest.selection import *
from echonest.sorting import *

from random import choice

from pprint import pprint

usage="""
    python dubstepize.py <inputfile> <outputfile> [<forced_key where 0 = C and 11 = B>]
"""

keys = {0: "C", 1: "C#", 2: "D", 3: "Eb", 4: "E", 5:"F", 6:"F#", 7:"G", 8:"G#", 9:"A", 10:"Bb", 11:"B"}
wubs = ['wubs/c.wav',
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
       ]

wub_breaks = ['break-ends/c.wav',
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
       ]
splashes = ['splashes/splash_03.wav',
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
       ]

scale = []

def mono_to_stereo(audio_data):
    data = audio_data.data.flatten().tolist()
    new_data = numpy.array((data,data))
    audio_data.data = new_data.swapaxes(0,1)
    audio_data.numChannels = 2
    return audio_data

def samples_of_key(section, key):   #HORRIBLY INEFFICIENT METHOD that should be fixed, eventually
    tries = 0
    while not len(samples[section][key]) and tries < 13:
        print "samples_of_key", section, key, tries
        if tries < 12:
            key = (key + 7) % 12
        else:
            key = tries % 12
        tries = tries + 1
   
    while not len(samples[section][key]):    #find-some-samples mode
        section = (section + 1) % len(samples)
        key = (key + 2) % 12

    return samples[section][key]

def loudness(segments, bar):
    b = segments.that(overlap_range(bar[0].start, bar[len(bar)-1].end))
    maximums = [x.loudness_max for x in b]
    if len(maximums):   
        return float(1 - pow(10, (max(maximums)/float(10))))
    else:
        return 1

samples = {}
def main(input_filename, output_filename, forced_key):
    
    sampling_target = "beats"   #could be bars, beats or tatums

    st = modify.Modify()
    nonwub = audio.LocalAudioFile(input_filename)
    print "Audio file analyzed."

    if not forced_key:
        tonic = nonwub.analysis.key['value']
    else:
        tonic = forced_key
    tempo = nonwub.analysis.tempo['value'] 

    fade_in = nonwub.analysis.end_of_fade_in
    fade_out = nonwub.analysis.start_of_fade_out

    bars = nonwub.analysis.bars#.that(are_contained_by_range(fade_in, fade_out))
    beats = nonwub.analysis.beats#.that(are_contained_by_range(fade_in, fade_out))  
    sections = nonwub.analysis.sections
    
    print "Selecting samples..."

    for i, v in enumerate(sections):
        samples[i] = {}
        for pitch in range(0, 12):
            sample_list = audio.AudioQuantumList()
            if sampling_target == "tatums":
                beat_list = audio.AudioQuantumList()
                beat_list.extend([b for x in v.children() for b in x.children()])
                sample_list.extend([b for x in beat_list for b in x.children()])
            elif sampling_target == "beats":
                sample_list.extend([b for x in v.children() for b in x.children()])
            elif sampling_target == "bars":
                sample_list.extend(v.children())
            samples[i][pitch] = sample_list.that(overlap_ends_of(nonwub.analysis.segments.that(have_pitch_max(pitch)).that(overlap_starts_of(sample_list))))

    audioout = audio.AudioData(shape= (len(nonwub),2), sampleRate=44100, numChannels=2)
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

    print "Grabbing wubwub samples..."

    introeight = audio.AudioData('samples/intro-eight.wav', sampleRate=44100, numChannels=2)
    hats       = audio.AudioData('samples/hats.wav', sampleRate=44100, numChannels=2)

    print "Compiling introduction..."

    custom_bars = []

    custom_bars.append(beats[0:4])
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
    
    nonwub_intro = mono_to_stereo(st.shiftTempo(audio.getpieces(nonwub, out), 140/tempo))
    nonwub_intro = audio.mix(nonwub_intro, introeight, 0.7)

    audioout.append(nonwub_intro)

    print "Compiling bars..."
######
#   BEGIN WUBWUB
######
#   Each "wub" comprises of 8 bars = 32 beats
#   of which, the default song format is:
#       1 1 1 1 1 1 1 1     =   8 wubs in tonic
#       4 4 4 4             =   4 wubs in the minor third from the tonic
#       10 10 10 10         =   4 wubs in the minor 7th from the tonic
######

    for section, value in enumerate(sections):
        print "\tCompiling bars for section", section+1 , "of", len(sections) , "..."
        onebar = audio.AudioQuantumList()
        s1 = samples_of_key(section, tonic)
        s2 = samples_of_key(section, (tonic + 3) % 12)
        s3 = samples_of_key(section, (tonic + 9) % 12)
        if sampling_target == "tatums":
            for twice in range(0, 2):
                for i in range(0, 16):
                    onebar.append( s1[i % len(s1)] )
                for i in range(16, 24):
                    onebar.append(  s2[i % len(s2)]  )
                for i in range(24, 32):
                    onebar.append(  s3[i % len(s3)]  )
        elif sampling_target == "beats":
            for twice in range(0, 2):
                for i in range(0, 8):
                    onebar.append( s1[i % len(s1)] )
                for i in range(8, 12):
                    onebar.append(  s2[i % len(s2)]  )
                for i in range(12, 16):
                    onebar.append(  s3[i % len(s3)]  )
        elif sampling_target == "bars":
            for i in range(0, 4):
                onebar.append( s1[i % len(s1)] )
            for i in range(4, 6):
                onebar.append(  s2[i % len(s2)]  )
            for i in range(6, 8):
                onebar.append(  s3[i % len(s3)]  )

        orig_bar = mono_to_stereo( st.shiftTempo( audio.getpieces(nonwub, onebar), 140/tempo ) )

        loud = loudness(nonwub.analysis.segments, onebar)

        basemix = 0.5      # 0 = full wub, 1 = full song

        mixfactor = (-1 * basemix) + loud
        print mixfactor
        if mixfactor < 0.3:
            mixfactor = 0.3

        audioout.append( audio.mix( audio.mix( audio.AudioData( wubs[tonic], sampleRate=44100, numChannels=2, verbose=False ), audio.AudioData( splashes[(section +1) % len(splashes)], sampleRate=44100, numChannels=2, verbose=False ) ), orig_bar , mixfactor ) )
        audioout.append( audio.mix( audio.mix( audio.AudioData( wub_breaks[tonic], sampleRate=44100, numChannels=2, verbose=False ), hats ), orig_bar , mixfactor ) )
    
    print "Adding ending..."

    audioout.append( audio.AudioData( splashes[(section +1) % len(splashes)], sampleRate=44100, numChannels=2, verbose=False ) )

    print "Encoding output..."

    audioout.encode( output_filename )

    print "Deleting temp file..."

    os.unlink(nonwub.convertedfile)

    print "Done!"

if __name__=='__main__':
    try:
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]
        if len(sys.argv) == 3:
            forced_key = int(sys.argv[3])
        else:
            forced_key = None
    except:
       input_filename = "aint.mp3"
       output_filename = "aint_debug.mp3"
       forced_key = None
    main(input_filename, output_filename, forced_key)

