# The Wub Machine #

The Wub Machine is a web/console app that automatically remixes music into Dubstep and Electro-House.

Check it out in action at [the.wubmachine.com](http://the.wubmachine.com/).

If you're interested, it's relatively simple to use this to create your own remixers and your own remix websites. Go nuts. :)

* [Prerequisites](#prerequisites)
  * [System Requirements](#system_requirements)
* [The Remixer](#the_remixer)
* [The Web Frontend](#the_web_frontend)
  * [Configuration](#configuration)
    * [Frontend Settings](#frontend_settings)
    * [Remix Queue Settings](#remix_queue_settings)
    * [Timeouts](#timeouts)
    * [Monitor Settings](#monitor_settings)
    * [Server Settings](#server_settings)
    * [Log Settings](#log_settings)
    * [File Extensions](#file_extensions)
    * [Socket.IO Settings](#socket_io_settings)
    * [SoundCloud Settings](#soundcloud_settings)
  * [Caveats & Other Notes](#caveats)

## <a name='prerequisites'>Prerequisites ##

The Wub Machine has only been tested on OS X and Ubuntu, but should theoretically work anywhere the dependencies are installed.
The installer script is currently a bit overzealous and installs a bunch of stuff, but *should* work.
You'll need an [API key from the Echo Nest](http://developer.echonest.com/account/register) to setup the Wub Machine, which you should then set as an environment variable ($ECHO_NEST_API_KEY).
The Wub Machine itself has a large list of dependencies, which the install.sh tries to setup:

 * [echonest-remix](https://github.com/echonest/remix)
 * ffmpeg
 * lame
 * soundstretch
 * shntool
 * [tornado](https://github.com/facebook/tornado)
 * [tornadio](https://github.com/MrJoes/tornadio)
 * libyaml
 * pyyaml
 * numpy
 * mutagen
 * libjpeg
 * PIL
 * python-mysqldb
 * sqlalchemy

### <a name='system_requirements'>System Requirements ###

I've gone to great lengths (well, ~50 lines) to make the Wub Machine as light as possible on system resources.
To remix a song **x** MB in size and **y** minutes long, expect:

* about 60MB * **y** in memory usage.
* at most 60MB * **y** in temporary disk space
* up to **x** MB of network bandwidth

In short, my 2-minute, 4MB test song uses up about 120MB of memory, about 100MB of disk space, and on first run, 4MB of upload bandwidth.

## <a name='the_remixer'>The Remixer ##

To remix from the command line, do:

    python -m remixers/dubstep <filename.[mp3|m4a|mp4|wav]>

or if you want to try ElectroHouse, do:

    python -m remixers/electrohouse <filename.[mp3|m4a|mp4|wav]>

The resulting file will be placed in the same folder as the original.

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

## <a name='the_web_frontend'>The Web Frontend

The web frontend uses Tornado, Tornadio (Socket.IO), MySQL, and a couple other things to allow people to remix over the web.
It has built-in SoundCloud sharing, [a neat monitoring/stats page](http://the.wubmachine.com/monitor), and plenty of tested features. However, it's still buggy, of course.
To get it up and running 100%, you'll need [an API key from SoundCloud](http://soundcloud.com/you/apps/new), which you can then place in config.yml.

Start the web frontend by doing:
    
    python server.py

There's also a very, very rough version of a daemonizer... if you want to start it and forget about it, run:

    python server.py start

To stop it, try running:
    
    python server.py stop

...although that probably won't work 100% of the time. In case of emergency, do:

    kill -9 `cat ./server.py.pid`

...and if that doesn't work, then find the pid with:

    ps aux | grep [p]ython

and kill the process.

### <a name='configuration'>Configuration ###

The web frontend makes use of a `yaml` file, `config.yml`, to dictate config variables at and during runtime. During runtime, you say? Why, yes!
`config.py` is a little bit of python metaprogramming that reloads each config variable as needed, only when it's changed. Simple.
What variables can you find in config.yml, you ask? Allow me to explain:

#### <a name='frontend_settings'>Frontend Settings ####
 * `app_name` is the public name of the app. i.e.: the Wub Machine, when running on my server, is called `the Wub Machine`. This is used in various places around the code.

#### <a name='remix_queue_settings'>Remix Queue Settings (can be changed on the fly) ####

 * `maximum_concurrent_remixes` is, well, the maximum number of remixes that *should* be running at any one time. Note that this is not strictly enforced while the remixer is running, but rather at each entrypoint to the queue. Certain race conditions may allow more than this number to be remixed at once. Ideally, set this to the number of cores you have on your machine. An entry-level Linode box can run 4 beautifully.
 * `maximum_waiting_remixes` dictates how many remixes should be allowed to wait in the queue. If this limit is reached, the homepage will refuse uploads for all new page loads. Pages that have already loaded are still allowed to add to the queue, and any pages that are closed while waiting will have their remixes deleted from the queue.
 * `hourly_remix_limit` is the number of remixes allowed in a given hour. Note that this is defined as the past 60 minutes, not as since the top of the hour.

#### <a name='timeouts'>Timeouts (all in seconds) ####
 * `cleanup_timeout` is the time between periodic cleans that delete remixes, uploads, and artwork.
 * `remix_timeout` is the maximum time a remix can take before being stopped/killed and deleted.
 * `wait_timeout` is the maximum time someone can wait for a remix before it is automatically deleted.
 * `watch_timeout` is the amount of time a browser has to open a progress socket (via Socket.io) after uploading a file. Otherwise, it is removed from the queue and deleted.

#### <a name='monitor_settings'>Monitor Settings ####
 * `monitor_limit` is the number of items to display upon initial load of the monitor page.
 * `monitor_time_limit` is the amount of time (in seconds) displayed on the graph.

#### <a name='server_settings'>Server Settings ####
 * `nginx` dictates if the app is running behind an Nginx proxy. Tornadio should have support for this, but I couldn't get it to work, so I rolled my own.
 * `database_connect_string` is the [SqlAlchemy database connection string](http://www.sqlalchemy.org/docs/core/engines.html#supported-databases) for your DB. Cannot be changed at runtime.

#### <a name='log_settings'>Log Settings ####
 * `log_file` is the name of the file to log all requests/warnings/errors/info to. This can be pretty verbose.
 * `log_name` is the name the server file should be referred to in the log file. (i.e.: `web` vs `remixer` vs `remixqueue`, etc.)
 * `log_format` is the format string of [Python LogRecord attributes](http://docs.python.org/library/logging.html#logrecord-attributes) to be used.
 * `echo_database_queries` is passed into SqlAlchemy's engine constructor to show database queries in the log file. This gets horribly verbose. Cannot be changed at runtime.

#### <a name='file_extensions'>File Extensions ####
 * `allowed_file_extensions` is a list of allowed file extensions, including periods. Limited to ['.mp3', '.m4a', '.mp4', '.wav'] by the Remix API at the moment.

#### <a name='socket_io_settings'>Socket.IO Settings ####
 * `socket_io_port` is what Socket.IO/Tornadio binds to, defaults to `8001`
 * `socket_extra_sep` is the separator between the Socket.IO URL and a resource ID (`watch`/`progress`/`UID`), defaults to `/`
 * `monitor_resource` is the name of the Monitor resource, defaults to `watch`
 * `progress_resource` is the name of the user-facing song progress resource, defaults to `progress`

#### <a name='soundcloud_settings'>SoundCloud Settings ####
 * `soundcloud_consumer` is your SoundCloud Consumer API key
 * `soundcloud_secret` is your SoundCloud secret API key (not sure if this is actually used anywhere, tbh)
 * `soundcloud_redirect` is the URL for SoundCloud to redirect to after OAuth login
 * `soundcloud_app_id` is the numeric app ID of your registered SoundCloud app - used to filter songs uploaded to SoundCloud.
 * `soundcloud_timeout` is the number of seconds before a SoundCloud upload times out.

 * `soundcloud_description` is the description tag automatically appended to any track shared to SoundCloud.
 * `soundcloud_tag_list` is a list of tags to be set on any shared tracks. Useful for filtering later.
 * `soundcloud_sharing_note` is the note used when sharing a track through SoundCloud to FB/Twitter.

### <a name='caveats'>Caveats & Other Notes ###
To edit the HTML markup, you can find the HTML templates in /templates. The SoundCloud widget on the homepage is mostly hardcoded, and the JS for that page is included in it... not very nice. But pretty fast. *There are rough edges all over this thing,* so please feel free to contribute. A lot of documentation is just not included.
