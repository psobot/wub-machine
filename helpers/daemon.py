import os, subprocess, sys, config

class Daemon():
    """
        Dirty little class to daemonize a script.
        Uses Linux/Unix/OS X commands to do its dirty work.
        Works for daemonizing a Tornado server, while other
        pythonic ways of daemonizing a process fail.
    """
    def __init__(self, pidfile=None):
        self.pidfile = "%s.pid" % sys.argv[0] if not pidfile else pidfile
        self.file = os.path.abspath(sys.argv[0])
        self.handleDaemon()

    def start(self):
        if os.path.exists('wubmachine.pid'):
            print '%s is already running!' % config.app_name
            exit(1)
        print ("Starting %s..." % config.app_name),
        devnull = open(os.devnull, 'w')
        pid = subprocess.Popen(
              ['nohup', 'python', self.file], 
              stdin=devnull,
              stdout=devnull,
              stderr=devnull 
            ).pid
        print "done. (PID: %s)" % pid
        open(self.pidfile, 'w').write(str(pid))

    def stop(self):
        if not os.path.exists(self.pidfile):
            print '%s is not running!' % config.app_name
        else:
            print ("Stopping %s..." % config.app_name),
            subprocess.Popen(['kill', '-2', open(self.pidfile).read()])
            print "done."
            if os.path.exists(self.pidfile):
                os.remove(self.pidfile)

    def handleDaemon(self):
        # The main process should be stopped only with a SIGINT for graceful cleanup.
        # i.e.: kill -2 `wubmachine.pid` if you really need to do it manually.

        if len(sys.argv) == 2:
            if sys.argv[1] == "start":    #   fast and cheap
                self.start()
                exit(0)
            elif sys.argv[1] == "stop":
                self.stop()
                exit(0)
            elif sys.argv[1] == 'restart':
                self.stop()
                self.start()
                exit(0)
