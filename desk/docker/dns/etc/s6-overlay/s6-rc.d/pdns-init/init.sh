#!/command/with-contenv sh

HOST_IP=$(hostname -i)
PDNS_DATA=${PDNS_DATA:-/var/services/powerdns}
PDNS_LOG=${PDNS_LOG:-/var/services/powerdns/log}
FQHOSTNAME=$(hostname)
mkdir -p "${PDNS_DATA}" "${PDNS_LOG}"

# /etc/desk/worker.conf is templated by worker-init, which has to finish before
# it registers the worker doc -- see the comment there.

# CONFIGURE PDNS
if grep -q "HOST_IP" "/etc/powerdns/pdns.d/pdns.local.conf"; then
    echo "* configure pdns"
    sed -i \
        -e "s/-HOST_IP-/${HOST_IP}/" \
        -e "s/-HOSTNAME-/${FQHOSTNAME}/" \
        -e "s#-PDNS_DATA-#${PDNS_DATA}#" \
        /etc/powerdns/pdns.d/*
fi

# SETUP PDNS DATABASE
if [ ! -f "${PDNS_DATA}/pdns_${FQHOSTNAME}.sqlite3" ]; then
    echo "* create pdns database: ${PDNS_DATA}/pdns_${FQHOSTNAME}.sqlite3"
    sqlite3 "${PDNS_DATA}/pdns_${FQHOSTNAME}.sqlite3" < /etc/powerdns/powerdns-setup.sql
fi

# pdns_server drops to setuid=pdns and needs to write the zone database and its
# journal, so the data directory and everything in it has to belong to pdns
chown -R pdns:pdns "${PDNS_DATA}"
