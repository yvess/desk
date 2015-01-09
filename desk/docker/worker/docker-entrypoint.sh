#!/bin/bash
#set -e

if [ "$1" = 'worker' ]; then
  if [ ! -f "/var/py27/lib/python2.7/site-packages/desk.egg-link" ]; then
    echo "adding desk to python packages"
    cd /projects/desk && /var/py27/bin/python setup.py develop
  fi
  WORKER_TYPE=${WORKER_TYPE:-worker} # set to worker as default
  if [ $WORKER_TYPE = "foreman" ]; then
    echo "setup foreman"
    wget -q --retry-connrefused -t 5 http://cdb:5984/ # wait for couchdb
    curl --head --silent -u admin:admin http://cdb:5984/desk_drawer | egrep "200 OK|401"
    if [ $? -ne 0 ]; then # db desk_drawer does not exist
        echo "creating desk_drawer database"
        cd /projects/desk/desk && /var/py27/bin/python ./dworker install-db
    fi
  fi
  exec /usr/sbin/runsvdir-start
fi

exec "$@"
