import config, os, time, database, traceback, logging
from helpers.web import ordinal
from datetime import datetime, timedelta

class RemixQueue():
    def __init__(self, monitor):
        self.log = logging.getLogger()
        self.monitor_callback = monitor.update

        self.remixers = {}
        self.finished = {}
        self.cleanups = {}

        self.watching = {}

        self.queue    = []
        self.running  = []

    def add(self, uid, ext, remixer, _user_callback, done_callback):
        self.log.debug("Adding remixer %s to queue..." % uid)
        if uid in self.remixers:
            raise Exception("Song already receieved!")

        infile = os.path.join("uploads/", "%s%s" % (uid, ext))
        outfile = os.path.join("static/songs/", "%s.mp3" % uid)

        user_callback = lambda data: _user_callback(uid, data)
        self.remixers[uid] = remixer(self, str(infile), str(outfile), [self.monitor_callback, user_callback])
        self.watching[uid] = user_callback
        self.cleanups[uid] = done_callback
        self.queue.append(uid)

    def updateTrack(self, uid, tag):
        # This may be called from another thread: let's use a unique DB connection.
        self.log.info("Updating track %s..." % uid)
        db = database.Session()
        try:
            track = db.query(database.Track).filter_by(uid = uid).first()
            keep = ['length', 'samplerate', 'channels', 'bitrate', 'title', 'artist', 'album', 'art', 'thumbnail']
            for a in tag:
                if a in keep:
                    try:
                        track.__setattr__(a, tag[a])
                    except:
                        pass
            db.commit()
            self.log.info("Track %s updated!" % uid)
        except:
            self.log.error("DB error when updating %s, rolling back:\n%s" % (uid, traceback.format_exc()))
            db.rollback()
            
    def finish(self, uid, final=None):
        self.log.debug("Finishing remixer %s from queue..." % uid)
        try:
            if not uid in self.remixers:
                return False
            if self.remixers[uid].isAlive():
                self.stop(uid)
            del self.remixers[uid]
            if not final:
                final = { 'status': -1, 'text': "Sorry, this remix is taking too long. Try again later!", 'progress': 0, 'uid': uid, 'time': time.time() }
            self.running.remove(uid)
            self.finished[uid] = final
            if self.cleanups[uid]:
                self.cleanups[uid](final)
                del self.cleanups[uid]
            
            # DB stuff
            db = database.Session()
            try:
                event = db.query(database.Event).filter_by(action='remix', uid=uid).first()
                event.end = datetime.now()
                if final['status'] is -1:
                    event.success = False
                    event.detail = final.get('debug')
                else:
                    event.success = True
                db.commit()
            except:
                db.rollback()
                self.log.error("DB error when finishing %s from queue:\n%s" % (uid, traceback.format_exc()))
            self.notifyWatchers()
            self.monitor_callback(uid)
            self.log.debug("Remixer %s finished! Calling next()..." % uid)
            self.next()
        except:
            self.log.error("Could not finish %s from queue:\n %s" % (uid, traceback.format_exc()))           

    def remove(self, uid):
        try:
            if uid in self.remixers:
                if self.remixers[uid].isAlive():
                    self.stop(uid)
                del self.remixers[uid]
                final = { 'status': -1, 'text': "Sorry, this remix is taking too long. Try again later!", 'progress': 0, 'uid': uid, 'time': time.time() }
                if uid in self.watching:
                    try:
                        self.watching(final)
                    except:
                        pass
                self.finished[uid] = final
                if self.cleanups[uid]:
                    self.cleanups[uid](None)
                    del self.cleanups[uid]
                # DB stuff
                db = database.Session()
                try:
                    event = db.query(database.Event).filter_by(action='remix', uid=uid).first()
                    if event:
                        event.end = datetime.now()
                        event.success = False
                        event.detail = "Timed out"
                    db.commit()
                except:
                    self.log.error("DB exception, rolling back:\n%s" % traceback.format_exc())
                    db.rollback()
                self.notifyWatchers()
                self.monitor_callback(uid)
            if uid in self.queue:
                self.queue.remove(uid)
            if uid in self.running:
                self.running.remove(uid)
            self.log.info("Removed %s from queue." % uid)
        except:
            self.log.error("Could not remove %s from queue:\n %s" % (uid, traceback.format_exc()))

    def start(self, uid):
        if not uid in self.queue:
            raise Exception("Cannot start, remixer not waiting: %s" % uid)
        if not self.remixers[uid].being_watched:
            raise Exception("Cannot start, nobody watching remixer: %s" % uid)
        self.running.append(uid)
        self.queue.remove(uid)
        del self.watching[uid]
        self.remixers[uid].start()

        db = database.Session()
        try:
            db.add(database.Event(uid, "remix"))
            db.commit()
        except:
            self.log.error("DB exception, rolling back:\n%s" % traceback.format_exc())
            db.rollback()
        self.monitor_callback(uid)
      

    def stop(self, uid):
        if uid in self.remixers and self.remixers[uid].isAlive():
            self.log.info("Stopping thread %s..." % uid)
            self.remixers[uid].stop()

    def notifyWatchers(self):
        for uid, callback in self.watching.iteritems():
            callback(self.waitingResponse(uid))

    def waitingResponse(self, uid):
        if uid in self.queue:
            position = self.queue.index(uid)
            if position is 0 and not len(self.running):
                text = "Starting..."
            elif position is 0 or position is 1:
                text = "Waiting... (next in line)"
            else:
                text = "Waiting in line... (%s)" % ordinal(position)
        else:
            text = "Starting..."
        return { 'status': 0, 'text': text, 'progress': 0, 'uid': uid, 'time': time.time() }

    def next(self):
        for uid in self.queue:
            if uid in self.watching:
                try:
                    self.start(uid)
                    self.log.info("Started remixer %s..." % uid)
                    break
                except:
                    pass
        else:
            self.log.info("No remixers in queue!")

    def cleanup(self):
        try:
            for uid, remixer in self.remixers.items():
                if config.watch_timeout and not remixer.started and not remixer.being_watched and remixer.added < (time.time() - config.watch_timeout):
                    self.log.info("Remixer %s is not being watched and has been waiting for more than %s seconds. Removing..." % (uid, config.watch_timeout)) 
                    self.remove(uid)
                elif config.wait_timeout and not remixer.started and remixer.added < (time.time() - config.wait_timeout):
                    self.log.info("Remixer %s has been waiting for more than %s minutes. Removing..." % (uid, config.wait_timeout/60)) 
                    self.remove(uid)
                elif config.remix_timeout and remixer.added < (time.time() - config.remix_timeout):
                    self.log.info("Remixer %s was added more than %s minutes ago. Removing..." % (uid, config.remix_timeout/60)) 
                    self.remove(uid)
                elif uid in self.running and not self.remixers[uid].isAlive():
                    self.log.info("Remixer %s is no longer alive. Removing..." % uid) 
                    self.remove(uid)
        except:
            self.log.error("RemixQueue cleanup went wrong:\n%s" % traceback.format_exc())

    def isAvailable(self):
        # Whatever condition this returns should result in next() being called once it no longer holds.
        # E.g.: If this returns False due to 25 remixers working, then at the end, next() should be called so the waiting remixer can start.
        return len(self.running) < config.maximum_concurrent_remixes

    def isAccepting(self):
        return len(self.queue) < config.maximum_waiting_remixes and self.countInHour() < config.hourly_remix_limit

    def countInHour(self):
        try:
            return len([v for k, v in self.finished.iteritems() if 'time' in v and v['time'] > time.time() - 3600])
        except:
            self.log.error("RemixQueue countInHour went wrong:\n%s\n%s" % (self.finished, traceback.format_exc()))
            return 0

    def errorRate(self):
        try:
            return len([r for r in self.finished if r.status == -1]) / len(r.finished)
        except:
            return 0

    def errorRateExceeded(self):
        return self.errorRate() > 0.5

