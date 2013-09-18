=======
Install
=======


CouchDB
=======

For ubuntu you can use the packages
https://launchpad.net/~nilya/+archive/couchdb-1.3
or build from source

For mac os x you can use macports.

Config
------

`/etc/couchdb/local.ini`

    [httpd]
    vhost_global_handlers = _utils, _uuids, _session, _oauth, _users, _rewrite, _desk_pad

    [couch_httpd_auth]
    require_valid_user = true

`/etc/couchdb/local.d/desk.ini`

    [httpd_global_handlers]
    _desk_pad = {couch_httpd_misc_handlers, handle_utils_dir_req, "/home/desk/src/desk/desk_pad"}

    [vhosts]
    desk.qs:5984 = /desk_drawer/_design/desk_drawer/_rewrite/


Desk
====

python
------

