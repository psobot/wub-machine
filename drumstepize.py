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

def mono_to_stereo(audio_data):
    data = audio_data.data.flatten().tolist()
    new_data = numpy.array((data,data))
    audio_data.data = new_data.swapaxes(0,1)
    audio_data.numChannels = 2
    return audio_data

def split_break(breakfile,n):
    drum_data = []
    start = 0
    for i in range(n):
        start = int((len(breakfile) * (i))/n)
        end = int((len(breakfile) * (i+1))/n)
        ndarray = breakfile.data[start:end]
        new_data = audio.AudioData(ndarray=ndarray,
                                    sampleRate=breakfile.sampleRate,
                                    numChannels=breakfile.numChannels)
        drum_data.append(new_data)
    return drum_data
    
def add_fade_out(segment_data):
    print "Adding fade out"
    when_max_volume = segment_data.data.argmax()
    samps_to_end = segment_data.endindex - when_max_volume
    linear_max_volume = pow(10.0,segment_data.data.max()/20.0)
    ss = 0
    cur_vol = float(linear_max_volume)
    if(samps_to_end > 0):
        how_much_volume_to_decrease_per_samp = linear_max_volume/float(samps_to_end)
        print how_much_volume_to_decrease_per_samp
        for samps in xrange(samps_to_end):
            cur_vol = cur_vol - how_much_volume_to_decrease_per_samp
            try:
                segment_data.data[ss] *= cur_vol
            except IndexError:
                pass
            ss = ss + 1
    return segment_data

def change_speed(aud, ratio):
    st = modify.Modify()
    r = mono_to_stereo(st.shiftTempo(aud, ratio))

    for i in aud.analysis.beats:
        i.start /= ratio
        i.duration /= ratio

    for i in aud.analysis.bars:
        i.start /= ratio
        i.duration /= ratio
    for i in aud.analysis.tatums:
        i.start /= ratio
        i.duration /= ratio
    for i in aud.analysis.sections:
        i.start /= ratio
        i.duration /= ratio
    for i in aud.analysis.segments:
        i.start /= ratio
        i.duration /= ratio
    r.analysis = aud.analysis
    r.analysis.tempo['value'] /= ratio
    return r

def main(input_filename, output_filename):
    nonstep = audio.LocalAudioFile(input_filename)
    nonstep.tempo = nonstep.analysis.tempo['value']
    nonstep.key = nonstep.analysis.key['value']

    pprint(nonstep.analysis.__dict__)
    nonstep = change_speed(nonstep, 140/nonstep.tempo)
    pprint(nonstep.analysis.__dict__)
    nonstep.encode('140input.mp3')
    sys.exit(1)

    step = audio.LocalAudioFile('dub.mp3')
    step.tempo = step.analysis.tempo['value']
    step.key = step.analysis.key['value']

    keydiff = step.key - nonstep.key
    if nonstep.key - step.key < keydiff:
        keydiff = nonstep.key - step.key
    if keydiff > 7:
        keydiff = keydiff - 12
    
    break_parts = 32# beats in break
    measures = 8 #bars in break

    audiofile = nonstep
    sample_rate = audiofile.sampleRate
    breakfile = step
    if breakfile.numChannels == 1:
        breakfile = mono_to_stereo(breakfile)
    num_channels = audiofile.numChannels
    st.setChannels(num_channels)
    drum_data = split_break(breakfile,break_parts)
    hits_per_beat = int(break_parts/(4 * measures))
    bars = audiofile.analysis.bars
    out_shape = (len(audiofile)+100000,num_channels)
    out = audio.AudioData(shape=out_shape, sampleRate=sample_rate,
                            numChannels=num_channels)

    mix = 0.5
    if not bars:
        print "Didn't find any bars in this analysis!"
        print "No output."
        sys.exit(-1)

    intro = audio.AudioQuantumList()

    beats = audiofile.analysis.beats
    custom_bars = []

    custom_bars.append(beats[0:4])
    custom_bars.append(beats[4:8])
    custom_bars.append(beats[8:12])
    custom_bars.append(beats[12:16])    

    intro.extend([x for bar in custom_bars for x in bar])
    
    intro.append(custom_bars[0][0])
    intro.append(custom_bars[0][0])
    intro.append(custom_bars[0][0])
    intro.append(custom_bars[0][0])
    
    intro.append(custom_bars[1][0])
    intro.append(custom_bars[1][0])
    intro.append(custom_bars[1][0])
    intro.append(custom_bars[1][0])


    beatone = custom_bars[2][0]
    beattwo = custom_bars[3][0]
    beatthree = custom_bars[3][2]
    
    for x in range(0, 8):
        intro.append(audio.AudioQuantum(beatone.start, beatone.duration/2, None, beatone.confidence, beatone.source))
    for x in range(0, 8):
        intro.append(audio.AudioQuantum(beattwo.start, beattwo.duration/4, None, beattwo.confidence, beattwo.source))
    for x in range(0, 8):
        intro.append(audio.AudioQuantum(beatthree.start, beatthree.duration/4, None, beatthree.confidence, beatthree.source))
    
    out.append(audio.getpieces(audiofile, intro))

    for bar in bars[16:-1]:
        beats = bar.children()
        for i in range(len(beats)):
            try:
                break_index = ((bar.local_context()[0] %\
                                measures) * 4) + (i % 4)
            except ValueError:
                break_index = i % 4
            tats = range((break_index) * hits_per_beat,
                        (break_index + 1) * hits_per_beat)
            drum_samps = sum([len(drum_data[x]) for x in tats])
            beat_samps = len(audiofile[beats[i]])
            beat_shape = (beat_samps,num_channels)
            tat_shape = (float(beat_samps/hits_per_beat),num_channels)
            beat_data= audio.AudioData(shape=beat_shape,
                                        sampleRate=sample_rate,
                                        numChannels=num_channels)
            for j in tats:
                tat_data= audio.AudioData(shape=tat_shape,
                                            sampleRate=sample_rate,
                                            numChannels=num_channels)
                if drum_samps > beat_samps/hits_per_beat:
                    # truncate drum hits to fit beat length
                    tat_data.data = drum_data[j].data[:len(tat_data)]
                elif drum_samps < beat_samps/hits_per_beat:
                    # space out drum hits to fit beat length
                    #temp_data = add_fade_out(drum_data[j])
                    tat_data.append(drum_data[j])
                    #tat_data.append(st.shiftTempo(drum_data[j], beat_samps/drum_samps))
                tat_data.endindex = len(tat_data)
                beat_data.append(tat_data)
                del(tat_data)
            # account for rounding errors
            beat_data.endindex = len(beat_data)
            mixed_beat = audio.mix(beat_data, audiofile[beats[i]], mix=mix)
            del(beat_data)
            out.append(mixed_beat)
    finale = bars[-1].start + bars[-1].duration
    last = audio.AudioQuantum(audiofile.analysis.bars[-1].start,
                            audiofile.analysis.duration - 
                              audiofile.analysis.bars[-1].start)
    last_data = audio.getpieces(audiofile,[last])
    out.append(last_data)
    out.encode(output_filename)

if __name__=='__main__':
    try:
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]
    except:
        sys.exit(-1)
    main(input_filename, output_filename)

