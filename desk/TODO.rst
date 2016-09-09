====
TODO
====

Worker
======

TASKS
=====

- clients deleted
- propogate failed order to frontend
- check for pdns logfile existens
- change to env vars for couchdb
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
- add client, without reload

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
