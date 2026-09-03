#!/command/with-contenv sh

WORKER_TYPE=${WORKER_TYPE:-worker} # set to worker as default
FQHOSTNAME=$(hostname)
WORKER_LOG=${WORKER_LOG:-/var/services/worker/log}
COUCHDB_ADMIN=${COUCHDB_ADMIN:-admin}
COUCHDB_ADMINPASS=${COUCHDB_ADMINPASS:-admin}
COUCHDB_HOST=${COUCHDB_HOST:-cdb}
COUCHDB_PORT=${COUCHDB_PORT:-5984}
PDNS_DATA=${PDNS_DATA:-/var/services/powerdns}
DNS_PRIMARY=${DNS_PRIMARY:-$FQHOSTNAME}

# CREATE DIRS
mkdir -p "$WORKER_LOG"

# CONFIGURE WORKER
# Every placeholder in worker.conf is filled in here, including the pdns ones in
# the dns image's copy: `install-worker` below writes `[worker] dns` into the
# worker doc, so a placeholder still standing at that point is registered
# verbatim and the worker then matches no task. pdns-init runs after this one.
if grep -q "COUCHDB_ADMINPASS" "/etc/desk/worker.conf"; then
    echo "* configure worker.conf"
    sed -i \
        -e "s#-COUCHDB_ADMINPASS-#${COUCHDB_ADMINPASS}#" \
        -e "s#-COUCHDB_ADMIN-#${COUCHDB_ADMIN}#" \
        -e "s#-COUCHDB_HOST-#${COUCHDB_HOST}#" \
        -e "s#-COUCHDB_PORT-#${COUCHDB_PORT}#" \
        -e "s#-HOSTNAME-#${FQHOSTNAME}#" \
        -e "s#-DNS_PRIMARY-#${DNS_PRIMARY}#" \
        -e "s#-PDNS_DATA-#${PDNS_DATA}#" \
      /etc/desk/worker.conf
fi

# RUN STUFF FOR FOREMAN, CREATE DATABASE
echo "WORKER_TYPE: $WORKER_TYPE"
echo "uri http://$COUCHDB_HOST:$COUCHDB_PORT/"
if [ $WORKER_TYPE = "foreman" ]; then
    wget -q --retry-connrefused -t 10 http://$COUCHDB_HOST:$COUCHDB_PORT/ # wait for couchdb to get up
    # idempotent: creates desk_drawer if missing, always refreshes the design doc
    cd /opt/app/desk && ./dworker install-db
    echo "* installed desk_drawer database and design doc"

    # Setup Fonts for invoices
    if [ -d "/root/.fonts" ]; then
        echo "* cleaning font cache"
        /usr/bin/fc-cache -f
    fi
fi

# REGISTER WORKER
# wait for the foreman to have created the database
until $(curl -Is -u $COUCHDB_ADMIN:$COUCHDB_ADMINPASS http://$COUCHDB_HOST:$COUCHDB_PORT/desk_drawer|cat|grep -q -E "HTTP.*200"); do
    sleep 1
    echo "* wait desk_drawer db"
done
curl -Is -u "${COUCHDB_ADMIN}:${COUCHDB_ADMINPASS}" "http://$COUCHDB_HOST:$COUCHDB_PORT/desk_drawer/worker-${FQHOSTNAME}"|cat|grep -q -E "HTTP.*404"
if [ $? -eq 0 ]; then # worker doesn't exist
    cd /opt/app/desk && ./dworker install-worker
    echo "* registred worker"
fi
