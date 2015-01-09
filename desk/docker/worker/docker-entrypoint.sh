#!/bin/bash
#set -e

if [ "$1" = 'worker' ]; then
  if [ ! -f "/var/py27/lib/python2.7/site-packages/desk.egg-link" ]; then
    echo "* adding desk to python packages"
    cd /projects/desk && /var/py27/bin/python setup.py develop
  fi
  WORKER_TYPE=${WORKER_TYPE:-worker} # set to worker as default
  if [ $WORKER_TYPE = "foreman" ]; then
    echo "* setup foreman"
    wget -q --retry-connrefused -t 5 http://cdb:5984/ # wait for couchdb
    # creating desk_drawer database
    curl -Is -u admin:admin http://cdb:5984/desk_drawer | egrep -q "HTTP.*200|HTTP.*401"
    if [ $? -ne 0 ]; then # db desk_drawer does not exist
        cd /projects/desk/desk && /var/py27/bin/python ./dworker install-db
        echo "* created desk_drawer database"
    fi
  fi
  # register worker
  curl -Is -u admin:admin http://cdb:5984/desk_drawer/worker-`hostname` | egrep -q "HTTP.*404"
  if [ $? -eq 0 ]; then # worker doesn't exist
    cd /projects/desk/desk && /var/py27/bin/python ./dworker install-worker
    echo "* registred worker"
  fi
  # setup worker
  if [ -f "/entrypoint-worker.sh" ]; then
    /entrypoint-worker.sh
  fi
  exec /usr/sbin/runsvdir-start
fi

exec "$@"
