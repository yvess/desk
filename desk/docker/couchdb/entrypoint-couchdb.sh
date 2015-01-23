#!/bin/bash

if [ -d "/root/build" ]; then
  # SET DEFAULT VALUES IF NOT SET
  VHOST_COUCHDB=${COUCHDB_DATA:-"desk.docker:5984"}

  # CONFIGURE PDNS
  if [ ! -f "/etc/couchdb/local.d/desk.ini" ]; then
    mv /root/build/desk.ini /etc/couchdb/local.d/
    sed -i -e "s#-VHOST_COUCHDB-#${VHOST_COUCHDB}#" \
      /etc/couchdb/local.d/desk.ini
  fi
fi
