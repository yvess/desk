#!/bin/sh

if [ -d "/root/build" ]; then
  # PREPARE STUFF
  echo "* setup dns"
  IP=$(hostname -i)
  PDNS_DATA=${PDNS_DATA:-/var/services/data/powerdns}
  PDNS_LOG=${PDNS_LOG:-/var/services/log/powerdns}
  DNS_PRIMARY=${DNS_PRIMARY:-$HOSTNAME}
  mkdir -p "$PDNS_DATA" "$PDNS_LOG"

  # CONFIGURE WORKER
  if [ ! -f "/etc/desk/worker.conf" ]; then
    echo "* configure worker.conf"
    cp /root/build/etc/worker.conf /etc/desk/worker.conf
    sed -i -e "s#-HOSTNAME-#${HOSTNAME}#" -e "s#-DNS_PRIMARY-#${DNS_PRIMARY}#" \
        -e "s#-PDNS_DATA-#${PDNS_DATA}#" \
      /etc/desk/worker.conf
  fi

  # CONFIGURE PDNS
  if [ ! -f "/etc/pdns.d/pdns.local.conf" ]; then
    echo "* configure pdns"
    cp /root/build/pdns.conf /etc/pdns.conf
    mkdir -p /etc/pdns.d/
    cp /root/build/pdns.local.* /etc/pdns.d/
    sed -i -e "s#-PDNS_DATA-#${PDNS_DATA}#" \
      /etc/pdns.d/pdns.local.gsqlite3.conf
    sed -i -e "s/-IP-/${IP}/" -e "s/-HOSTNAME-/${HOSTNAME}/" \
      /etc/pdns.d/*
  fi

  # SETUP PDNS DATABASE
  if [ ! -f "$PDNS_DATA/pdns_$(hostname).sqlite3" ]; then
    sqlite3 $PDNS_DATA/pdns_$(hostname).sqlite3 < /root/build/powerdns-setup.sql
  fi

  # CONFIGURE RUNIT PDNS
  if [ ! -f "/etc/service/pdns" ]; then
    sed -i -e "s#-PDNS_LOG-#${PDNS_LOG}#" \
      /root/build/service/pdns/run
  fi

  # ACTIVATE RUNIT SERVICE
  echo "* added runit pdns"
  [ ! -d "/etc/service/pdns" ] && cp -R /root/build/service/pdns /etc/service/
fi
