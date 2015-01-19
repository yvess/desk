#!/bin/bash

if [ -d "/root/build" ]; then
  # SETUP WORKER SCRIPT
  echo "* setup dns"
  IP=`hostname -i`

  # CONFIGURE PDNS
  if [ ! -f "/etc/powerdns/pdns.d/pdns.local.conf" ]; then
    mv /root/build/pdns.local.conf /root/build/pdns.local.gsqlite3.conf /etc/powerdns/pdns.d/
    sed -i -e "s/-IP-/${IP}/" -e "s/-HOSTNAME-/${HOSTNAME}/" \
      /etc/powerdns/pdns.d/*
    rm /etc/powerdns/bindbackend.conf /etc/powerdns/pdns.d/pdns.simplebind.conf
  fi

  # SETUP PDNS DATABASE
  if [ -f "/var/services/data/powerdns/pdns_`hostname`.sqlite3" ]; then
    sqlite3 /var/services/data/powerdns/pdns_`hostname`.sqlite3 < /root/build/powerdns-setup.sql
  fi
fi
