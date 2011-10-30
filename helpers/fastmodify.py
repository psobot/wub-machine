"""
fastmodify.py

Provides similar functionality to echonest.Modify, but faster and lighter.
Requires soundstretch command-line binary to be installed.

Based on code by Ben Lacker on 2009-06-12.
Modified by Peter Sobot for speed on 2011-08-12
"""
from echonest.audio import *
import uuid, os

class FastModify():
    def processAudio( self, ad, arg, tempdir="tmp/" ):
        if not os.access( tempdir, os.W_OK ):
            tempdir = './'
        u = str( uuid.uuid1() )
        ad.encode( '%s%s.wav' % ( tempdir, u ) )
        process = subprocess.Popen(   ['soundstretch', '%s%s.wav' % ( tempdir, u ), '%s%s.out.wav' % ( tempdir, u ), arg],
                            stdin=None,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
        process.wait()
        os.unlink( '%s%s.wav' % ( tempdir, u ) )
        ad = AudioData( '%s%s.out.wav' % ( tempdir, u ), verbose=False )
        os.unlink( '%s%s.out.wav' % ( tempdir, u ) )
        return ad

    def shiftTempo(self, audio_data, ratio):
        if not isinstance(audio_data, AudioData):
            raise TypeError('First argument must be an AudioData object.')
        if not (isinstance(ratio, int) or isinstance(ratio, float)):
            raise ValueError('Ratio must be an int or float.')
        if (ratio < 0) or (ratio > 10):
            raise ValueError('Ratio must be between 0 and 10.')
        return self.processAudio(audio_data, '-tempo=%s' % float((ratio-1)*100))

