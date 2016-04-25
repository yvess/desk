.PHONY:

couchdb_version = 1.6.1
worker_version = 0.1
dns_version = 0.1

default: build_couchdb build_worker build_dns

build_couchdb:
	docker build -t yvess/desk-couchdb:$(couchdb_version) couchdb

build_worker:
	docker build -t yvess/desk-worker:$(worker_version) worker

build_dns:
	docker build -t yvess/desk-dns:$(dns_version) dns

data:
	docker create -v /var/services --name desk_data busybox true

pull:
	docker pull yvess/desk-couchdb
	docker pull yvess/desk-worker
	docker pull yvess/desk-dns

setup: build_couchdb build_worker build_dns data

fig_test:
	cd ../ && fig run foreman
