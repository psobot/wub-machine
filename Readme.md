The Wub Machine
===============

The Wub Machine is a Python app that attempts to create a dubstep remix of any song.
It's implemented as a web app (behind a Tornado-based frontend) at http://the.wubmachine.com/

This is its algorithm and backend code, and can be easily integrated as part of a larger Python app.
(Currently only tested on OS X and Ubuntu, but should work anywhere the dependencies are installed.)

Usage
-----
To remix from the command line, use:

    python dubstep.py <filename.[mp3|m4a|wav|aif]>

To integrate with a larger app, simply do something like:
    
    from dubstep import Dubstep
    class MyProject():
        def wubwub( self ):
            remixer = Dubstep( self, "song.mp3", "output.mp3", ".mp3", "some-kinda-uid", self.log )
            remixer.deleteOriginal = False
            remixer.start()

        def log( self, update ):
            print "Hey look, progress from the remixer!"
            print update
    m = MyProject()
    m.wubwub()

The Remix superclass uses a separate thread to monitor progress, and spawns a new process from that thread to do the heavy lifting.
If you want to create a new remixer, you can modify the Dubstep class to remix however you want.

System Requirements
-------------------
I've gone to great lengths (well, ~50 lines) to make the Wub Machine as light as possible on system resources.
First off, a couple binaries need to be installed on your system:

* lame (very fast, high-quality MP3 encoding)
* shntool (very, very fast merging of .wav files)
* soundstretch (fast and light tempo modifications)

As well, to remix a song x MB in size and y minutes long expect:

* about 60MB * y in memory usage.
* at most 60MB * y in temporary disk space
* up to x MB of network bandwidth

In short, my 2-minute, 4MB test song uses up about 120MB of memory, about 100MB of disk space, and on first run, 4MB of upload bandwidth.
