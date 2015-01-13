#!/bin/bash

if [ -d "/root/build" ]; then
  echo "* setup dns"
  IP=`hostname -i`
  # move & delete some files
  mv /root/build/service/pdns /etc/service/pdns
  mv /root/build/pdns.local.conf /root/build/pdns.local.gsqlite3.conf /etc/powerdns/pdns.d/
  sed -i -e "s/-IP-/${IP}/" -e "s/-HOSTNAME-/${HOSTNAME}/" \
    /etc/powerdns/pdns.d/*
  rm /etc/powerdns/bindbackend.conf /etc/powerdns/pdns.d/pdns.simplebind.conf
  # setup sqlitedatabase
  if [ -f "/var/services/data/powerdns/pdns_`hostname`.sqlite3" ]; then
    sqlite3 /var/services/data/powerdns//pdns_`hostname`.sqlite3 < /root/build/powerdns-setup.sql
  fi
fi
