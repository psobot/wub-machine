import config, os, database, traceback, time

class Cleanup():
    directories = ['tmp', 'uploads', 'static/songs']
    keep = ['thumb', 'empty']
    artdir = "static/songs"
    log = None
    db = None
    remixQueue = None

    def __init__(self, log, remixQueue):
        self.log = log
        self.remixQueue = remixQueue

    def all(self):
        for d in self.directories:
            if not os.path.exists(d):
                self.log.info("\t\Creating directory %s..." % d)
                os.mkdir(d)
            else:
                self.log.info("\t\tPurging directory %s..." % d)
                for f in os.listdir(d):
                    if not any([k in f for k in self.keep]):
                        p = os.path.join(d, f)
                        self.log.info("\t\t\tRemoving %s..." % p)
                        try:
                            os.remove(p)
                        except:
                            self.log.warning("Failed to remove %s:\n%s" % (p, traceback.format_exc()))
                            pass
        self.thumbnails()

    def active(self):
        self.log.info("Cleaning up...")
        for uid, remixer in self.remixQueue.finished.items():
            # If remix was last touched within cleanup_timeout seconds, leave it alone
            if 'time' in remixer and remixer['time'] > (time.time() - config.cleanup_timeout):
                continue
            self.log.info("\tClearing: %s" % uid)
            for d in self.directories:
                for f in os.listdir(d):
                    if uid in f and not any([k in f for k in self.keep]):
                        p = os.path.join(d, f)
                        self.log.info("\t\tRemoving %s..." % f)
                        os.remove(p)
            del self.remixQueue.finished[uid]
        self.thumbnails()

    def thumbnails(self):
        self.log.info("\tRemoving old thumbnails...")
        db = database.Session()
        try:
            thumbs = [os.path.basename(thumb) for (thumb,) in db.query(database.Track.thumbnail).order_by(database.Track.id.desc()).limit(config.monitor_limit).all() if thumb is not None]
            for f in os.listdir(self.artdir):
                if os.path.basename(f) not in thumbs:
                    p = os.path.join(self.artdir, f)
                    self.log.info("\t\tRemoving %s..." % p)
                    os.remove(p)
        except:
            self.log.error("DB read exception:\n%s" % traceback.format_exc())
