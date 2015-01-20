#!/bin/bash
#set -e

if [ "$1" = 'worker' ]; then
  # ADDING DESK TO PYTHON PATH
  if [ ! -f "/var/py27/lib/python2.7/site-packages/desk.egg-link" ]; then
    echo "* adding desk to python packages"
    cd /opt/app && /var/py27/bin/python setup.py develop > /dev/null
  fi
  WORKER_TYPE=${WORKER_TYPE:-worker} # set to worker as default
  TESTING=${TESTING:-false}

  # RUN SETUP WORKER SCRIPT
  if [ -f "/entrypoint-worker.sh" ]; then
    /entrypoint-worker.sh
  fi

  # RUN IN TEST CASE
  if [ "$TESTING" ]; then
    shift
    exec "$@"
  # DON'T RUN IN TEST CASE
  else
    # RUN STUFF FOR FOREMAN, CREATE DATABASE
    if [ $WORKER_TYPE = "foreman" ]; then
      echo "* setup foreman"
      wget -q --retry-connrefused -t 10 http://cdb:5984/ # wait for couchdb to get up
      # creating desk_drawer database
      curl -Is -u admin:admin http://cdb:5984/desk_drawer | egrep -q "HTTP.*200|HTTP.*401"
      if [ $? -ne 0 ]; then # db desk_drawer does not exist
          cd /opt/app/desk && /var/py27/bin/python ./dworker install-db
          echo "* created desk_drawer database"
      fi
    fi

    # EDIT WORKER.CONF
    if grep -qv -e "-HOSTNAME-" /etc/desk/worker.conf; then
      echo "* update worker.conf"
      sed -i -e "s/-HOSTNAME-/`hostname`/" /etc/desk/worker.conf
    fi

    # REGISTER WORKER
    # wait for db created
    until $(curl -Is -u admin:admin http://cdb:5984/desk_drawer|egrep -q "HTTP.*200"); do
      sleep 1
      echo "* wait desk_drawer db"
    done
    curl -Is -u admin:admin http://cdb:5984/desk_drawer/worker-`hostname` | egrep -q "HTTP.*404"
    if [ $? -eq 0 ]; then # worker doesn't exist
      cd /opt/app/desk && /var/py27/bin/python ./dworker install-worker
      echo "* registred worker"
    fi

    # ACTIVATE RUNIT SERVICES
    [ ! -d "/etc/service/worker" ] && mv /root/build/service/* /etc/service/
    # cleanup
    rm -Rf /root/build
    exec /usr/sbin/runsvdir-start
  fi
fi

exec "$@"
