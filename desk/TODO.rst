====
TODO
====

Worker
======

TASKS
=====

- check for pdns logfile existence
- permission sqlitedb pdns_controll
- update clients, without reload
- cache map_ips
- waring if unsaved content exists
- check if domain is already taken
- fix client assignment for new domains

ENHANCEMENTS
============

- add couchdb migrations, active -> activated
- check for pdns logfile existence
- autosetup db if it doesn't exists
- add update validators
- previous version template update on template change
- cleanup template doc befor merge
- use_doc for all plugins
- permission sqlitedb
- validate couchdb doc for dns
- doc strings
- check affected rows from sql
- undo queue feature
- generic cache doc
- add order nothing todo
- visualize doc state
- reset powerdns domain

BUGS
====

- client name doesn't updates automatic in dns

REFACTOR
========

- change everything to command from cmd

STATES
======

states:
 - new
 - changed
 - active
 - failed
 - delete
 - deleted
