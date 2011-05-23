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

import echonest.audio as audio
from echonest import modify
from echonest.selection import *
from echonest.sorting import *

from random import choice

from pprint import pprint

usage="""
"""

keys = {0: "C", 1: "C#", 2: "D", 3: "Eb", 4: "E", 5:"F", 6:"F#", 7:"G", 8:"G#", 9:"A", 10:"Bb", 11:"B"}
wubs = [audio.AudioData('wubs/c.wav',       sampleRate=44100, numChannels=2),
        audio.AudioData('wubs/c-sharp.wav', sampleRate=44100, numChannels=2),
        audio.AudioData('wubs/d.wav',       sampleRate=44100, numChannels=2),
        audio.AudioData('wubs/d-sharp.wav', sampleRate=44100, numChannels=2),
        audio.AudioData('wubs/e.wav',       sampleRate=44100, numChannels=2),
        audio.AudioData('wubs/f.wav',       sampleRate=44100, numChannels=2),
        audio.AudioData('wubs/f-sharp.wav', sampleRate=44100, numChannels=2),
        audio.AudioData('wubs/g.wav',       sampleRate=44100, numChannels=2),
        audio.AudioData('wubs/g-sharp.wav', sampleRate=44100, numChannels=2),
        audio.AudioData('wubs/a.wav',       sampleRate=44100, numChannels=2),
        audio.AudioData('wubs/a-sharp.wav', sampleRate=44100, numChannels=2),
        audio.AudioData('wubs/b.wav',       sampleRate=44100, numChannels=2)
       ]

wub_breaks = [audio.AudioData('break-ends/c.wav',       sampleRate=44100, numChannels=2),
        audio.AudioData('break-ends/c-sharp.wav', sampleRate=44100, numChannels=2),
        audio.AudioData('break-ends/d.wav',       sampleRate=44100, numChannels=2),
        audio.AudioData('break-ends/d-sharp.wav', sampleRate=44100, numChannels=2),
        audio.AudioData('break-ends/e.wav',       sampleRate=44100, numChannels=2),
        audio.AudioData('break-ends/f.wav',       sampleRate=44100, numChannels=2),
        audio.AudioData('break-ends/f-sharp.wav', sampleRate=44100, numChannels=2),
        audio.AudioData('break-ends/g.wav',       sampleRate=44100, numChannels=2),
        audio.AudioData('break-ends/g-sharp.wav', sampleRate=44100, numChannels=2),
        audio.AudioData('break-ends/a.wav',       sampleRate=44100, numChannels=2),
        audio.AudioData('break-ends/a-sharp.wav', sampleRate=44100, numChannels=2),
        audio.AudioData('break-ends/b.wav',       sampleRate=44100, numChannels=2)
       ]

scale = []

def mono_to_stereo(audio_data):
    data = audio_data.data.flatten().tolist()
    new_data = numpy.array((data,data))
    audio_data.data = new_data.swapaxes(0,1)
    audio_data.numChannels = 2
    return audio_data

def samples_of_key(section, key):
    tries = 0
    while not len(samples[section][key]) and tries < 24:
        if tries < 12:
            key = (key + 7) % 12
        else:
            key = tries % 12
        tries = tries + 1
   
    while not len(samples[section][key]):    #find-some-samples mode
        section = (section + 1) % len(samples)
        key = (key + 2) % 12

    return samples[section][key]

def loudness(beat):
    data = beat.render()
    if data.numChannels == 2:
        return float( max( [ abs(x) for x, y in data.data ] ) ) / 32768
    else:
        return float( max( [ abs(x) for x in data.data ] ) ) / 32768

samples = {}
def main(input_filename, output_filename, forced_key):
    
    sampling_target = "beats"   #could be bars, beats or tatums

    st = modify.Modify()
    nonwub = audio.LocalAudioFile(input_filename)
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


#    for i, s in enumerate(nonwub.analysis.bars):
#        audio.getpieces(nonwub, [s]).encode("bar_%s_%s" % (i, output_filename))

    low        = audio.AudioData('samples/sub_long01.wav', sampleRate=44100, numChannels=2)
    fizzle     = audio.AudioData('samples/fizzle.wav', sampleRate=44100, numChannels=2)
    fizzle_soft= audio.AudioData('samples/fizzle-soft.wav', sampleRate=44100, numChannels=2)
    introeight = audio.AudioData('samples/intro-eight.wav', sampleRate=44100, numChannels=2)
    hats       = audio.AudioData('samples/hats.wav', sampleRate=44100, numChannels=2)
    blank      = audio.AudioData('samples/empty.wav', sampleRate=44100, numChannels=2)

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
    nonwub_intro = audio.mix(nonwub_intro, low, 0.7)
    nonwub_intro = audio.mix(nonwub_intro, introeight, 0.7)

    audioout.append(nonwub_intro)
 
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
        onebar = audio.AudioQuantumList()
        if sampling_target == "tatums":
            for twice in range(0, 2):
                for i in range(0, 16):
                    s = samples_of_key(section, tonic)
                    onebar.append( s[i % len(s)] )
                for i in range(16, 24):
                    s = samples_of_key(section, (tonic + 3) % 12)
                    onebar.append(  s[i % len(s)]  )
                for i in range(24, 32):
                    s = samples_of_key(section, (tonic + 9) % 12)
                    onebar.append(  s[i % len(s)]  )
        elif sampling_target == "beats":
            for twice in range(0, 2):
                for i in range(0, 8):
                    s = samples_of_key(section, tonic)
                    onebar.append( s[i % len(s)] )
                for i in range(8, 12):
                    s = samples_of_key(section, (tonic + 3) % 12)
                    onebar.append(  s[i % len(s)]  )
                for i in range(12, 16):
                    s = samples_of_key(section, (tonic + 9) % 12)
                    onebar.append(  s[i % len(s)]  )
        elif sampling_target == "bars":
            for i in range(0, 4):
                s = samples_of_key(section, tonic)
                onebar.append( s[i % len(s)] )
            for i in range(4, 6):
                s = samples_of_key(section, (tonic + 3) % 12)
                onebar.append(  s[i % len(s)]  )
            for i in range(6, 8):
                s = samples_of_key(section, (tonic + 9) % 12)
                onebar.append(  s[i % len(s)]  )

        orig_bar = mono_to_stereo( st.shiftTempo( audio.getpieces(nonwub, onebar), 140/tempo ) )

        loud = loudness(orig_bar)

        basemix = 0.5      # 0 = full wub, 1 = full song

        mixfactor = (-1 * basemix) + loud
        if mixfactor < 0.3:
            mixfactor = 0.3

        audioout.append( audio.mix( audio.mix( wubs[tonic], fizzle ), orig_bar , mixfactor ) )
        audioout.append( audio.mix( audio.mix( wub_breaks[tonic], hats ), orig_bar , mixfactor ) )
    
    audioout.append( fizzle_soft )
    audioout.encode( output_filename )


if __name__=='__main__':
    try:
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]
        if len(sys.argv) > 3:
            forced_key = int(sys.argv[3])
        else:
            forced_key = None
    except:
        print usage
        sys.exit(-1)
    main(input_filename, output_filename, forced_key)

