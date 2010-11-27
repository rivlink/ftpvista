### BEGIN INIT INFO
# Provides:          ftpvista.sh
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Start FTPVista
# Description:       FTPVista
### END INIT INFO

DAEMON=/home/ftpvista/ftpvista3/ftpvista/ftpvista.py
PID=/var/run/ftpvista.pid
DESC=FTPVista

test -x $DAEMON || exit 0

set -e

case "$1" in
  start)
    echo -n "Starting $DESC: "
    start-stop-daemon --start --quiet --exec $DAEMON
    ;;
  stop)
    echo -n "Stopping $DESC: "
    start-stop-daemon --stop --quiet --pidfile $PID
    ;;
  restart|force-reload)
    echo -n "Restarting $DESC: "
    start-stop-daemon --stop --quiet --pidfile $PID
    start-stop-daemon --start --quiet --exec $DAEMON
    ;;
  status)
      if pidofproc -p "$PIDFILE" >/dev/null; then
          log_action_end_msg 0 "running"
              exit 0
      else
          if [ -e "$PIDFILE" ]; then
              log_action_end_msg 1 "failed to start"
              exit 1
          else
              log_action_end_msg 0 "not running"
              exit 3
          fi
      fi
      ;;
  *)
    N=/etc/init.d/$NAME
    echo "Usage: $N {start|stop|restart|reload|force-reload|status}" >&2
    exit 1
    ;;
esac

exit 0