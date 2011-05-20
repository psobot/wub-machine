####################################################################################
#
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
# 
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
# 
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# 
# ####################################################################################
 
import echonest.audio as audio
import numpy as N
import os, sys
import os.path as path
import random as r
from pprint import pprint
 
class DonkRemix(object):
    def __init__(self, input, kick, donk, snare, clap, ohh, chh, ratio, output):
        self.input      = input
        self.output     = output
        self.ratio      = float(ratio)
        
        count = 0
        
        self.audio      = audio.LocalAudioFile(input)
        self.beats      = self.audio.analysis.beats
        self.sections   = self.audio.analysis.sections
        self.bars       = self.audio.analysis.bars
        self.tempo      = self.audio.analysis.tempo['value']
        
        self.data       = self.audio.data.swapaxes(0, 1)
        self.samplerate = self.audio.sampleRate
        self.nchannels  = N.min(2, len(self.data))
        
        self.fade_in    = int(self.audio.analysis.end_of_fade_in * self.samplerate)
        print "Fade in = %s" % self.audio.analysis.end_of_fade_in
        
        self.kick       = audio.AudioData(kick, sampleRate=44100, numChannels=2)
        self.kickdata   = self.kick.data.swapaxes(0, 1)
 
        self.donk       = audio.AudioData(donk, sampleRate=44100, numChannels=2)
        self.donkdata   = self.donk.data.swapaxes(0, 1)
        
        self.snare      = audio.AudioData(snare, sampleRate=44100, numChannels=2)
        self.snaredata  = self.snare.data.swapaxes(0, 1)
        
        self.clap       = audio.AudioData(clap, sampleRate=44100, numChannels=2)
        self.clapdata   = self.clap.data.swapaxes(0, 1)
        
        self.ohh        = audio.AudioData(ohh, sampleRate=44100, numChannels=2)
        self.ohhdata    = self.ohh.data.swapaxes(0, 1)
    
        self.chh        = audio.AudioData(chh, sampleRate=44100, numChannels=2)
        self.chhdata    = self.chh.data.swapaxes(0, 1)
        
        self.current_section = -1
        self.changed_section = False
    
        pprint(self.beats)


        self.preprocess()
        self.process()
        # TODO postprocess
        self.write()
        
    def preprocess(self):
        for buffer in [ self.data, self.kickdata, self.snaredata, self.ohhdata ]:
            for channel in range(len(buffer)):
                buffer[channel] *= 0.6
 
    def process(self):
        self.add_kicks()
    #    self.add_donks()
        self.add_snares()
      #  self.add_hihats()
       # self.add_cuts()
        
    def add_kicks(self):
        for index, beat in enumerate(self.beats):
            try:
                frames = int(beat.start * self.samplerate)
                endframes = int(beat.end * self.samplerate)
            
                self.update_current_section(frames)
              #  if self.changed_section:
              #      hold = r.randint(0, 3) == 0
 
                if frames >= self.fade_in:# and not hold:            
                    for channel in range(self.nchannels):
                        max = frames + len(self.kickdata[channel])
                        self.data[channel][frames:max] += self.kickdata[channel]
            except:
                pass
                print "error adding kick", index
                    
    def add_donks(self):
        for index, beat in enumerate(self.beats):
            try:
                frames                  = int(beat.start * self.samplerate)
                endframes               = int(beat.end * self.samplerate)
                dur                     = endframes - frames
                mid                     = int(frames + (dur / 2))
            
                self.update_current_section(mid)
             #   if self.changed_section:
             #       hold    = r.randint(0, 3) == 0
                    
                if not hold:
                    for channel in range(self.nchannels):
                        max = mid + len(self.donkdata[channel])
                        self.data[channel][mid:max] += self.donkdata[channel]
            except:
                pass
                print "error adding donks to section", index
                
    def add_snares(self):
        for index, beat in enumerate(self.beats):
            indexInBar, length      = beat.local_context()
            frames                  = int(beat.start * self.samplerate)

            self.update_current_section(frames)
          #  if self.changed_section:
          #      randomIndex = r.randint(0, 1)
          #      data = [ self.snaredata, self.clapdata ][randomIndex]
          #      hold = r.randint(0, 2) == 0
            if self.current_section > 0:# and not hold:
                if indexInBar % 2 == 1:
                    for channel in range(self.nchannels):
                        max = frames + len(self.snaredata[channel])
                        self.data[channel][frames:max] += self.snaredata[channel]
                        
    def add_hihats(self):        
        for index, beat in enumerate(self.beats):
            try:
                frames                  = int(beat.start * self.samplerate)
                endframes               = int(beat.end * self.samplerate)
                dur                     = endframes - frames
                mid                     = int(frames + (dur / 2))
            
                self.update_current_section(mid)
                if self.changed_section:
                    randomIndex = r.randint(0, 1)
                    data    = [ self.ohhdata, self.chhdata ][randomIndex]
                    hold    = r.randint(0, 2) == 0
                if self.current_section > 1 and not hold:
                    for channel in range(self.nchannels):
                        max = mid + len(data[channel])
                        self.data[channel][mid:max] += data[channel]
            except:
                pass
                print "error adding hihats to section", index
                    
    def add_cuts(self):
        for index, section in enumerate(self.sections):
            if r.randint(0, 3) > 0: # kick drum roll
                try:
                    lastbar     = section.children()[-1]
                    for beat in lastbar.children():
                        frames      = int(beat.start * self.samplerate)
                        endframes   = int(beat.end * self.samplerate)
                        dur         = endframes - frames
                        mid         = int(frames + (dur / 2))
                        
                        for channel in range(self.nchannels):
                            max = mid + len(self.kickdata[channel])
                            self.data[channel][mid:max] += (self.kickdata[channel] * 0.5)
                    
                except:
                    pass
                    print "Exception processing kick drum roll for section", index                    
            else:                   # cuts
                reverse = r.randint(0, 1) == 0
                try:
                    lastbar     = section.children()[-1]
                    firsttatum  = lastbar.children()[0].children()[0]
                    ftstart     = int(firsttatum.start * self.samplerate)
                    ftend       = int(firsttatum.end * self.samplerate)
            
                    for beat in lastbar.children():
                        for tatum in beat.children():
                            frames = int(tatum.start * self.samplerate)
                            max    = int(tatum.end * self.samplerate)
                            dur    = int(tatum.duration * self.samplerate)
                    
                            for channel in range(self.nchannels):
                                data = self.data[channel][ftstart:ftstart+(max-frames)]
                                self.data[channel][frames:max] = data
                except:
                    pass
                    print "Exception processing cuts for section", index
                    
        for index, section in enumerate(self.sections):
            try:
                if r.randint(0, 4) == 0: # reverse last bar
                    lastbar     = section.children()[-1]
                    start       = int(lastbar.start * self.samplerate)
                    endbeat     = lastbar.children()[-1]
                    end         = int(endbeat.end * self.samplerate)
 
                    for channel in range(self.nchannels):
                        self.data[channel][start:end] = self.data[channel][start:end][::-1]
            except:
                pass
                print "Error reversing section", index
 
    def update_current_section(self, frames):
        for section in reversed(self.sections):
            start = int(section.start * self.samplerate)
            if start <= frames:
                new_section = section.local_context()[0]
                if not new_section == self.current_section:
                    self.changed_section = True
                    self.current_section = new_section
                else:
                    self.changed_section = False
                return
        
    def write(self):
        if float(self.tempo * self.ratio) < 130 and float(self.ratio) > 1.0:
            diff = 140.0 / (self.tempo * self.ratio)
            self.ratio *= diff
        self.audio.sampleRate *= self.ratio
        self.audio.encode(self.output)
 
 
if __name__ == "__main__":
    pprint(sys.argv[1:])
    remix = DonkRemix(*sys.argv[1:])

