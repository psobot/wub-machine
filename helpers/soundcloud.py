import config, tornado.httpclient, json, time, logging, traceback
from random import choice

class SoundCloud():
    tracks =            []
    trackage =          None
    log = None

    supermassive = {
        'title' :         "Supermassive Black Hole (Wub Machine Remix)",
        'uri' :           "http://api.soundcloud.com/tracks/17047599",
        'permalink_url' : "http://soundcloud.com/plamere/supermassive-black-hole-wub",
        'artwork_url' :   "http://i1.sndcdn.com/artworks-000008186991-lnrin1-large.jpg?dd4912a",
        'created_with' :  {"id": config.soundcloud_app_id}
    }
    def __init__(self, log):
        self.log = log
        self.ht = tornado.httpclient.AsyncHTTPClient()
        self.fetchTracks()
    
    def fetchTracks(self):
        self.log.info("\tFetching SoundCloud tracks...")
        self.ht.fetch('https://api.soundcloud.com/tracks.json?client_id=%s&tags=wubmachine&order=created_at&limit=30&license=no-rights-reserved&filter=downloadable' % config.soundcloud_consumer, self._fetchTracks)

    def _fetchTracks(self, response):
        try:
            if not response.error:
                tracks = json.loads(response.body)
                self.tracks = [e for e in tracks if self.valid(e)]
                self.trackage = time.gmtime()
                self.log.info("SoundCloud tracks received!")
            else:
                self.log.error("SoundCloud fetch resulted in error: %s" % response.error)
        except:
            self.log.error("SoundCloud track update failed completely with an exception:\n%s" % traceback.format_exc())

    def frontPageTrack(self):
        if choice(xrange(0, 4)) % 4 and self.tracks:
            track = choice(self.tracks)
        else:
            track = self.supermassive
        return track

    def valid(self, track):
        return (track['created_with']['id'] == config.soundcloud_app_id) and (track['title'] != "[untitled] (Wub Machine Remix)") and (len(track['title']) > 20) and (len(track['title']) < 60)

