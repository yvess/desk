#!/bin/sh

if [ -d "/root/build" ]; then
  # PREPARE STUFF
  echo "* setup pdns"
  HOST_IP=$(hostname -i)
  PDNS_DATA=${PDNS_DATA:-/var/services/data/powerdns}
  PDNS_LOG=${PDNS_LOG:-/var/services/log/powerdns}
  DNS_PRIMARY=${DNS_PRIMARY:-$HOSTNAME}
  mkdir -p "$PDNS_DATA" "$PDNS_LOG"

  # CONFIGURE WORKER
  if [ grep "PDNS_DATA" "/etc/desk/worker.conf" ]; then
    echo "* configure worker.conf"
    sed -i -e "s#-HOSTNAME-#${HOSTNAME}#" -e "s#-DNS_PRIMARY-#${DNS_PRIMARY}#" \
        -e "s#-PDNS_DATA-#${PDNS_DATA}#" \
        /etc/desk/worker.conf
  fi

  # CONFIGURE PDNS
  if [ grep "/etc/pdns.d/pdns.local.conf" "HOST_IP" ]; then
    echo "* configure pdns"
    sed -i -e "s#-PDNS_DATA-#${PDNS_DATA}#" \
        /etc/pdns.d/pdns.local.gsqlite3.conf
    sed -i -e "s/-HOST_IP-/${HOST_IP}/" -e "s/-HOSTNAME-/${HOSTNAME}/" \
        /etc/pdns.d/*
  fi

  # SETUP PDNS DATABASE
  if [ ! -f "$PDNS_DATA/pdns_$(hostname).sqlite3" ]; then
      sqlite3 $PDNS_DATA/pdns_$(hostname).sqlite3 < /etc/pdns/powerdns-setup.sql
  fi
fi
