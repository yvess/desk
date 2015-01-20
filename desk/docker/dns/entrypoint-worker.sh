#!/bin/bash

if [ -d "/root/build" ]; then
  # PREPARE STUFF
  echo "* setup dns"
  IP=$(hostname -i)
  PDNS_DATA=${PDNS_DATA:-/var/services/data/powerdns}
  mkdir -p "$PDNS_DATA"
  rm /etc/powerdns/pdns.d/pdns.local.conf

  # CONFIGURE PDNS
  if [ ! -f "/etc/powerdns/pdns.d/pdns.local.conf" ]; then
    mv /root/build/pdns.local.conf /root/build/pdns.local.gsqlite3.conf /etc/powerdns/pdns.d/
    sed -i -e "s#-PDNS_DATA-#${PDNS_DATA}#" \
      /etc/powerdns/pdns.d/pdns.local.gsqlite3.conf
    sed -i -e "s/-IP-/${IP}/" -e "s/-HOSTNAME-/${HOSTNAME}/" \
      /etc/powerdns/pdns.d/*
    rm /etc/powerdns/bindbackend.conf /etc/powerdns/pdns.d/pdns.simplebind.conf
  fi

  # SETUP PDNS DATABASE
  if [ ! -f "$PDNS_DATA/pdns_$(hostname).sqlite3" ]; then
    sqlite3 $PDNS_DATA/pdns_$(hostname).sqlite3 < /root/build/powerdns-setup.sql
  fi

  # ACTIVATE RUNIT SERVICES
  echo "* added runit pdns"
  [ ! -d "/etc/service/pdns" ] && mv /root/build/service/pdns /etc/service/
fi
