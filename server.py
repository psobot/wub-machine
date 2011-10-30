"""
    The Wub Machine
    Python web interface
    started August 5 2011 by Peter Sobot (petersobot.com)
"""

__author__ = "Peter Sobot"
__copyright__ = "Copyright (C) 2011 Peter Sobot"
__version__ = "2.2"

import json, time, locale, traceback, gc, logging, os, database, urllib
import tornado.ioloop, tornado.web, tornado.template, tornado.httpclient, tornado.escape, tornado.websocket
import tornadio, tornadio.server
import config
from datetime import datetime, timedelta
from hashlib import md5

# Wubmachine-specific libraries
from helpers.remixqueue import RemixQueue
from helpers.soundcloud import SoundCloud
from helpers.cleanup import Cleanup
from helpers.daemon import Daemon
from helpers.web import *

# Kinds of remixers.
from remixers.dubstep import Dubstep
from remixers.electrohouse import ElectroHouse
remixers = {
  'Dubstep': Dubstep,
  'ElectroHouse': ElectroHouse
}

# Check dependencies...
# Check required version numbers
assert tornado.version_info >= (2, 0, 0), "Tornado v2 or greater is required!"
assert tornadio.__version__ >= (0, 0, 4), "Tornadio v0.0.4 or greater is required!"

# Instead of using xheaders, which doesn't seem to work under Tornadio, we do this:
if config.nginx:
    class RequestHandler(tornado.web.RequestHandler):
        """
            Patched Tornado RequestHandler to take care of Nginx ip proxying
        """
        def __init__(self, application, request, **kwargs):
            if 'X-Real-Ip' in request.headers:
                request.remote_ip = request.headers['X-Real-Ip']
            tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
else:
    RequestHandler = tornado.web.RequestHandler

# Handlers

class MainHandler(RequestHandler):
    def get(self):
        js = ("window.wubconfig = %s;" % json.dumps(config.javascript)) + javascripts
        kwargs = {
            "isOpen": r.isAccepting(),
            "track": sc.frontPageTrack(),
            "isErroring": r.errorRateExceeded(),
            'count': locale.format("%d", trackCount, grouping=True),
            'cleanup_timeout': time_in_words(config.cleanup_timeout),
            'javascript': js,
            'connectform': connectform
        }
        self.write(templates.load('index.html').generate(**kwargs)) 
    def head(self):
        self.finish()

class ProgressSocket(tornadio.SocketConnection):
    listeners = {}

    @classmethod
    def update(self, uid, data):
        try:  
            self.listeners[uid].send(data)
        except:
            pass

    def on_open(self, *args, **kwargs):
        try:
            self.uid = kwargs['extra']
            if self.uid in r.finished:
                try:
                    self.close()
                except:
                    pass
            else:
                self.listeners[self.uid] = self
                if self.uid in r.remixers:
                    r.remixers[self.uid].being_watched = True
                    log.info("Remixer %s is now being watched..." % self.uid)
                r.cleanup()
                if r.isAvailable():
                    try:
                        r.start(self.uid)
                    except:
                        self.send({ 'status': -1, 'text': "Sorry, something went wrong. Please try again later!", 'progress': 0, 'uid': self.uid, 'time': time.time() })
                        self.close()
                log.info("Opened progress socket for %s" % self.uid)
        except:
            log.error("Failed to open progress socket for %s because: %s" % (self.uid, traceback.format_exc()) )

    def on_close(self):
        try:
            log.info("Progress socket for %s received on_close event. Stopping..." % self.uid)
            try:
                r.stop(self.uid)
            except:
                pass
            if self.uid in r.remixers:
                r.remixers[self.uid].being_watched = False
            if self.uid in self.listeners:
                del self.listeners[self.uid]
            log.info("Closed progress socket for %s" % self.uid)
        except:
          log.warning("Failed to close progress socket for %s due to:\n%s" % (self.uid, traceback.format_exc()))

    def on_message(self, message):
        pass

class MonitorSocket(tornadio.SocketConnection):
    monitors = set()

    @classmethod
    def update(self, uid):
        try:
            if self.monitors:
                data = MonitorHandler.track(uid)
            for m in self.monitors.copy():
                try:  
                    m.send(data.decode('utf-8'))
                    m.send(MonitorHandler.overview())
                except:
                    log.error("Failed to send data to monitor.")
        except:
            log.error("Major failure in MonitorSocket.update.")

    def on_open(self, *args, **kwargs):
        log.info("Opened monitor socket.")
        self.monitors.add(self)

    def on_close(self):
        log.info("Closed monitor socket.")
        self.monitors.remove(self)

    def on_message(self, message):
        pass

class MonitorHandler(RequestHandler):
    keys = ['upload', 'download', 'remixTrue', 'remixFalse', 'shareTrue', 'shareFalse']

    @tornado.web.asynchronous
    def get(self, sub=None, uid=None):
        if sub:
            sections = {
                'graph': self.graph,
                'overview': self.overview,
                'latest': self.latest,
                'remixqueue': self.remixqueue,
                'timespan' : self.timespan
            }
            if sub in sections:
                self.write(sections[sub]())
                self.finish()
            else:
                raise tornado.web.HTTPError(404)
        else:
            kwargs = {
                'overview': self.overview(),
                'latest': self.latest(),
                'config': "window.wubconfig = %s;" % json.dumps(config.javascript)
            }
            self.write(templates.load('monitor.html').generate(**kwargs))
            self.finish()

    def clearqueue(self):
        del self.watchqueue[:]

    @classmethod
    def histogram(self, interval=None):
        db = database.Session()
        try:
            query = db.query(database.Event).add_columns('count(*)', database.Event.action, database.Event.success).group_by('action', 'success')
            if interval:
                limit = datetime.now() - timedelta(**{ interval: 1 })
                d = query.filter(database.Event.start > limit).all()
            else:
                d = query.all()
            n = {}
            for k in self.keys:
                n[k] = 0
            for a in d:
                if a.action == 'upload' or a.action == 'download':
                    n[a.action] = int(a.__dict__['count(*)'])
                elif a.action == 'remix' or a.action == 'share':
                    n["%s%s" % (a.action, a.success)] = int(a.__dict__['count(*)'])
            return n
        except:
            log.error("DB read exception:\n%s" % traceback.format_exc())
            return {}

    def remixqueue(self):
        self.set_header("Content-Type", 'text/plain')
        return str("Remixers: %s\nFinished: %s\nQueue:    %s\nRunning:  %s" % (r.remixers, r.finished, r.queue, r.running))

    @classmethod
    def overview(self):
        kwargs = {
            'ct': str(datetime.now()),
            'inqueue': len(r.queue),
            'processing': len(r.running),
            'maximum': config.maximum_concurrent_remixes,
            'maximumexceeded': len(r.remixers) > config.maximum_concurrent_remixes,
            'hourly': config.hourly_remix_limit,
            'hourlyexceeded': r.countInHour() >= config.hourly_remix_limit,
            'errorInterval': 1,
            'errorRate': r.errorRate(),
            'errorRateExceeded': r.errorRateExceeded(),
            'isOpen': r.isAccepting(),
            'hour': MonitorHandler.histogram('hours'),
            'day': MonitorHandler.histogram('days'),
            'ever': MonitorHandler.histogram(),
        }
        return templates.load('overview.html').generate(**kwargs)

    def current(self):
        running = [v for k, v in r.remixers.iteritems() if k in r.running]
        return templates.load('current.html').generate(c=running)

    def shared(self):
        db = database.Session()
        try:
            d = db.query(database.Event).filter_by(action = "sharing", success = True).group_by(database.Event.uid).order_by(database.Event.id.desc()).limit(6).all()
        except:
            log.error("DB read exception:\n%s" % traceback.format_exc())
        return templates.load('shared.html').generate(tracks=d)

    @classmethod
    def track(self, track):
        db = database.Session()

        if not track:
            raise tornado.web.HTTPError(400)

        if isinstance(track, database.Track):
            try:
                track = db.merge(track)
            except:
                log.error("DB read exception:\n%s" % traceback.format_exc())
                db.rollback()
        else:
            if isinstance(track, dict) and 'uid' in track:
                track = track['uid']
            elif not isinstance(track, str) or len(track) != 32:
                return ''
            try:
                tracks =  db.query(database.Track).filter(database.Track.uid == track).all()
            except:
                log.error("DB read exception:\n%s" % traceback.format_exc())
                db.rollback()
            if not tracks:
                return ''
            else:
                track = tracks[0]

        for stat in ['upload', 'remix', 'share', 'download']:
            track.__setattr__(stat, None)
        
        events = {}
        for event in track.events:
            events[event.action] = event
        track.upload = events.get('upload')
        track.remix = events.get('remix')
        track.share = events.get('share')
        track.download = events.get('download')
        track.running = track.uid in r.running or (track.share and track.share.start and not track.share.end and track.share.success is None)
        track.failed = (track.remix and track.remix.success == False) or (track.share and track.share.success == False)
        if track.failed:
            if track.remix.success is False:
                track.failure = track.remix.detail 
            elif track.share.detail is not None:
                track.failure = track.share.detail
            else:
                track.failure = ''
        try:
            track.progress = r.remixers[track.uid].last['progress']
            track.text = r.remixers[track.uid].last['text']
        except:
            track.progress = None
            track.text = None

        kwargs = {
            'track': track,
            'exists': os.path.exists,
            'time_ago_in_words': time_ago_in_words,
            'seconds_to_time': seconds_to_time,
            'convert_bytes': convert_bytes
        }
        return templates.load('track.html').generate(**kwargs)

    def latest(self):
        db = database.Session()
        try:
            tracks = db.query(database.Track).order_by(database.Track.id.desc()).limit(config.monitor_limit).all()
        except:
            log.error("DB read exception, rolling back:\n%s" % traceback.format_exc())
            db.rollback()
        return ''.join([self.track(track) for track in tracks])

    def timespan(self):
        start = float(self.get_argument('start'))
        end = float(self.get_argument('end'))
        
        if end - start < 0:
            raise tornado.web.HTTPError(400)
        elif end - start > config.monitor_time_limit:
            start = end - config.monitor_time_limit

        db = database.Session()
        try:
            tracks = db.query(database.Track).filter(database.Track.time < datetime.fromtimestamp(end)).filter(database.Track.time > datetime.fromtimestamp(start)).order_by(database.Track.id.desc()).all()
        except:
            log.error("DB read exception, rolling back:\n%s" % traceback.format_exc())
            db.rollback()
        return ''.join([self.track(track) for track in tracks])

    def graph(self):
        history = {}
        db = database.Session()
        for i in xrange(1, 24*2): # last 3 days
            low = datetime.now() - timedelta(hours = i)
            high = low + timedelta(hours = 1)
            timestamp = 1000 * time.mktime(high.timetuple())
            try:
                dayr = db.query(database.Event).add_columns('count(*)', database.Event.action, database.Event.success).group_by('action', 'success').filter(database.Event.start.between(low, high)).all()
                n = {}
                for daya in dayr:
                    if daya.action == 'download':
                        n[daya.action] = [timestamp , int(daya.__dict__['count(*)'])]
                    elif daya.action == 'remix' or daya.action == 'share':
                        n["%s%s" % (daya.action, daya.success)] = [timestamp, int(daya.__dict__['count(*)'])]

                for k in self.keys:
                    if not k in history:
                        history[k] = []
                    if k in n:
                        history[k].append(n[k])
                    else:
                        history[k].append([timestamp, int(0)])
            except:
                log.error("DB read exception, rolling back:\n%s" % traceback.format_exc())
                db.rollback()
        return history 

class ShareHandler(RequestHandler):
    @tornado.web.asynchronous
    def get(self, uid):
        self.uid = uid
        try:
            token = str(self.get_argument('token'))
            timeout = config.soundcloud_timeout
            self.event = database.Event(uid, "share", ip = self.request.remote_ip) 

            if not uid in r.finished:
                raise tornado.web.HTTPError(404)

            t = r.finished[uid]['tag']

            description = config.soundcloud_description
            if 'artist' in t and 'album' in t and t['artist'].strip() != '' and t['album'].strip() != '':
                description = ("Original song by %s, from the album \"%s\".<br />" % (t['artist'].strip(), t['album'].strip())) + description
            elif 'artist' in t and t['artist'].strip() != '':
                description = ("Original song by %s.<br />" % t['artist'].strip()) + description

            form = MultiPartForm()
            form.add_field('oauth_token', token)
            form.add_field('track[title]', t['new_title'].encode('utf-8'))
            form.add_field('track[genre]', t['style'])
            form.add_field('track[license]', "no-rights-reserved")
            form.add_field('track[tag_list]', ' '.join(['"%s"' % tag for tag in config.soundcloud_tag_list]))
            form.add_field('track[description]', description.encode('utf-8'))
            form.add_field('track[track_type]', 'remix')
            form.add_field('track[downloadable]', 'true')
            form.add_field('track[sharing_note]', config.soundcloud_sharing_note)
            form.add_file('track[asset_data]', '%s.mp3' % uid, open(t['remixed']))

            if 'tempo' in t:
                form.add_field('track[bpm]', t['tempo'])
            if 'art' in t:
                form.add_file('track[artwork_data]', '%s.png' % uid, open(t['art']))
            if 'key' in t:
                form.add_field('track[key_signature]', t['key'])

            MonitorSocket.update(self.uid)

            self.ht = tornado.httpclient.AsyncHTTPClient()
            self.ht.fetch(
                "https://api.soundcloud.com/tracks.json",
                self._get,
                method = 'POST',
                headers = {"Content-Type": form.get_content_type()},
                body = str(form),
                request_timeout = timeout,
                connect_timeout = timeout
            )
        except:
            self.write({ 'error': traceback.format_exc().splitlines()[-1] })
            self.event.success = False
            self.event.end = datetime.now()
            self.event.detail = traceback.format_exc()
            MonitorSocket.update(self.uid)
        finally:
            db = database.Session()
            try:
                db.add(self.event)
                db.commit()
            except:
                log.error("DB exception, rolling back:\n%s" % traceback.format_exc())
                db.rollback()
    
    def _get(self, response):
        self.write(response.body)
        self.finish()
        r = json.loads(response.body)
        try:
            db = database.Session()
            self.event = db.merge(self.event)
            self.event.success = True
            self.event.end = datetime.now()
            self.event.detail = r['permalink_url'].encode('ascii', 'ignore')
            db.commit()
        except:
            log.error("DB exception, rolling back:\n%s" % traceback.format_exc())
            db.rollback()
        MonitorSocket.update(self.uid)
        sc.fetchTracks()

class DownloadHandler(RequestHandler):
    def get(self, uid):
        if not uid in r.finished or not os.path.isfile('static/songs/%s.mp3' % uid):
            raise tornado.web.HTTPError(404)
        else:
            db = database.Session()
            try:
                uploader = db.query(database.Event.ip).filter_by(uid = uid, action = "upload").first()[0]
            except:
                log.error("DB exception, rolling back:\n%s" % traceback.format_exc())
                db.rollback()
                uploader = self.request.remote_ip
            if uploader != self.request.remote_ip:
                log.error("Download attempt on remix %s by IP %s, not uploader %s!" % (uid, self.request.remote_ip, uploader))
                raise tornado.web.HTTPError(403)
            filename = "%s.mp3" % (r.finished[uid]['tag']['new_title'] if 'new_title' in r.finished[uid]['tag'] else uid)
            self.set_header('Content-disposition', 'attachment; filename="%s"' % filename)
            self.set_header('Content-type', 'audio/mpeg')
            self.set_header('Content-Length', os.stat('static/songs/%s.mp3' % uid)[6])
            self.write(open('static/songs/%s.mp3' % uid).read())
            self.finish()
            try:
                db.add(database.Event(uid, "download", success = True, ip = self.request.remote_ip))
                db.commit()
            except:
                log.error("DB exception, rolling back:\n%s" % traceback.format_exc())
                db.rollback()
            MonitorSocket.update(uid)

class UploadHandler(RequestHandler):
    def trackDone(self, final):
        # [TODO]: Why is this here? Move this somewhere more appropriate.
        global trackCount
        trackCount += 1
        if self.uid in ProgressSocket.listeners:
            log.info("Closing client connection for track %s..." % self.uid)
            ProgressSocket.listeners[self.uid].close()
            log.info("Closed client connection for track %s." % self.uid)

    def post(self):
        self.uid = config.uid()
        try:
            remixer = remixers[self.get_argument('style')]
        except:
            log.error("Error when trying to handle upload: %s" % traceback.format_exc())
            self.write({ "error" : "No remixer type specified!" })
        
        self.track = database.Track(self.uid, style=self.get_argument('style'))
        self.event = database.Event(self.uid, "upload", None, self.request.remote_ip, urllib.unquote_plus(self.get_argument('qqfile').encode('ascii', 'ignore')))

        try:
            extension = os.path.splitext(self.get_argument('qqfile'))[1]
        except:
            extension = '.mp3'
        self.track.extension = extension
        targetPath = os.path.join('uploads/', '%s%s' % (self.uid, extension))

        if extension not in config.allowed_file_extensions:
            self.write({ 'error': "Sorry, but %s only works with %s." % (config.app_name, list_in_words([e[1:] for e in config.allowed_file_extensions])) })
            return

        try:
            f = open(targetPath, 'w')
            data = self.request.body if not self.request.files else self.request.files['upload'][0]['body'] 
            f.write(data)
            f.close()

            self.track.hash = md5(data).hexdigest()
            self.track.size = len(data)
            del data

            if not self.request.files:
                del self.request.body
            else:
                del self.request.files['upload'][0]['body']

            r.add(self.uid, extension, remixer, ProgressSocket.update, self.trackDone)
            self.event.success = True
            response = r.waitingResponse(self.uid)
            response['success'] = True
            self.write(response)
        except Exception as e:
            log.error("Error when trying to handle upload: %s" % traceback.format_exc())
            self.write({ "error" : "Could not save file." })
            self.event.success = False
        self.event.end = datetime.now()

        db = database.Session()
        try:
            db.add(self.track)
            db.add(self.event)
            db.commit()
        except:
            log.error("DB exception, rolling back:\n%s" % traceback.format_exc())
            db.rollback()

        MonitorSocket.update(self.uid)
        gc.collect()

application = tornado.web.Application([
    (r"/(favicon.ico)", tornado.web.StaticFileHandler, {"path": "static/img/"}),
    (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": "static/"}),
    (r"/monitor[/]?([^/]+)?[/]?(.*)", MonitorHandler), #Fix this
    (r"/upload", UploadHandler),
    (r"/share/(%s)" % config.uid_re, ShareHandler),
    (r"/download/(%s)" % config.uid_re, DownloadHandler),
    (r"/", MainHandler),
    tornadio.get_router(
        MonitorSocket,
        resource = config.monitor_resource
    ).route(),
    tornadio.get_router(
        ProgressSocket,
        resource = config.progress_resource,
        extra_re = config.uid_re,
        extra_sep = config.socket_extra_sep
    ).route()],
    socket_io_port = config.socket_io_port,
    enabled_protocols = ['websocket', 'xhr-multipart', 'xhr-polling', 'jsonp-polling'],
    )


if __name__ == "__main__":
    Daemon()

    log = logging.getLogger()
    log.name = config.log_name
    handler = logging.FileHandler(config.log_file)
    handler.setFormatter(logging.Formatter(config.log_format)) 
    handler.setLevel(logging.DEBUG)
    log.addHandler(handler)

    try:
        log.info("Starting %s..." % config.app_name)
        try:
            locale.setlocale(locale.LC_ALL, 'en_US.utf8')
        except:
            locale.setlocale(locale.LC_ALL, 'en_US')
        
        log.info("\tConnecting to MySQL...")
        db = database.Session()
        if not db:
            log.critical("Can't connect to DB!")
            exit(1)

        log.info("\tGrabbing track count from DB...")
        trackCount = db.query(database.Event).filter_by(action='remix', success = True).count()

        log.info("\tClearing temp directories...")
        cleanup = Cleanup(log, None)
        cleanup.all()

        log.info("\tStarting RemixQueue...")
        r = RemixQueue(MonitorSocket)
        cleanup.remixQueue = r

        log.info("\tInstantiating SoundCloud object...")
        sc = SoundCloud(log)

        log.info("\tLoading templates...")
        templates = tornado.template.Loader("templates/")
        templates.autoescape = None

        log.info("\tStarting cleanup timers...")
        fileCleanupTimer = tornado.ioloop.PeriodicCallback(cleanup.active, 1000*config.cleanup_timeout)
        fileCleanupTimer.start()
        
        queueCleanupTimer = tornado.ioloop.PeriodicCallback(r.cleanup, 100*min(config.watch_timeout, config.remix_timeout, config.wait_timeout))
        queueCleanupTimer.start()

        log.info("\tCaching javascripts...")
        javascripts = '\n'.join([
            open('./static/js/jquery.fileupload.js').read(),
            open('./static/js/front.js').read(),
            open('./static/js/player.js').read(),
        ])
        connectform = open('./static/js/connectform.js').read()

        log.info("\tStarting Tornado...")
        application.listen(8888)
        log.info("...started!")
        tornadio.server.SocketServer(application, xheaders=config.nginx)
    except:
        raise
    finally:
        log.critical("Error: %s" % traceback.format_exc())
        log.critical("IOLoop instance stopped. About to shutdown...")
        try:
            cleanup.all()
        except:
            pass
        log.critical("Shutting down!")
        if os.path.exists('server.py.pid'):
            os.remove('server.py.pid')
        exit(0)

