#!/usr/bin/python
import sys
from netTel import netTel
import logging

PIDFILE = '/var/run/netTelD.pid'
WORKFOLDER = '/var/lib/netTel/'

if __name__ == "__main__":

    daemon = netTel(PIDFILE, loglevel=logging.DEBUG, home_dir=WORKFOLDER, stdout=WORKFOLDER+'netTel.log', stderr=WORKFOLDER+'netTel.log')

    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            try:
                daemon.start()
            except:
                pass

        elif 'stop' == sys.argv[1]:
            daemon.stop()

        elif 'restart' == sys.argv[1]:
            daemon.restart()

        elif 'status' == sys.argv[1]:
            daemon.is_running()

        else:
            print "Unknown command"
            print "usage: %s start|stop|restart|status" % sys.argv[0]
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart|status" % sys.argv[0]
        sys.exit(2)
