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
PID2=/var/run/ftpvista_online_checker.pid
DESC=FTPVista

test -x $DAEMON || exit 0

set -e

case "$1" in
  start-online-checker)
    echo -n "Starting $DESC Online Checker: "
    start-stop-daemon --start --quiet --exec $DAEMON --pidfile $PID2 -- -o
    ;;
  stop-online-checker)
    start-stop-daemon --stop --quiet --pidfile $PID2
    ;;
  restart-online-checker)
    echo -n "Restarting $DESC: "
    start-stop-daemon --stop --quiet --pidfile $PID2
    start-stop-daemon --start --quiet --exec $DAEMON --pidfile $PID2 -- -o
    ;;
  start)
    echo -n "Starting $DESC: "
    start-stop-daemon --start --quiet --exec $DAEMON --pidfile $PID
    ;;
  stop)
    echo -n "Stopping $DESC: "
    start-stop-daemon --stop --quiet --pidfile $PID
    ;;
  restart)
    echo -n "Restarting $DESC: "
    start-stop-daemon --stop --quiet --pidfile $PID
    start-stop-daemon --start --quiet --exec $DAEMON --pidfile $PID
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
    echo "Usage: $N {start|stop|restart|start-online-checker|stop-online-checker|restart-online-checker|status}" >&2
    exit 1
    ;;
esac

exit 0