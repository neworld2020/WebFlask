
project_port=5000

usage(){
  echo "Usage: sh $0 [start|stop|restart]"
  exit 1
}

is_running(){
  # running -- return 0, else return 1
  pid=$(netstat -tnlp --numeric-hosts | grep :project_port | awk '{print $7}' | awk -F/ '{print $1}')
  if [ -z "${pid}" ]; then
    return 1
  else
    return 0
  fi
}

start(){
  is_running
  if [ $? -eq "0" ]; then
    # running -- no need to start again
    echo "Program is running"
  else
    # start program
    echo "Program start"
    # 1. install packages
    python3 -m pip install -r requirements.txt
    # 2. start program
    python3 app.py
    exit 0
  fi
}

stop(){
  is_running
  if [ $? -eq "0" ]; then
    echo "Program stop"
    # running -- stop
    kill -15 "$pid"
  else
    echo "Program is not running"
  fi
}

restart(){
  stop
  sleep 3
  start
}

case "$1" in
 "start")
 start
 ;;
 "stop")
 stop
 ;;
 "restart")
 restart
 ;;
 *)
 usage
 ;;
esac



