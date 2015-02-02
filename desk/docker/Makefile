default: build_couchdb build_worker build_dns

build_couchdb:
	docker build -t yvess/desk-couchdb couchdb

build_worker:
	docker build -t yvess/desk-worker worker

build_dns:
	docker build -t yvess/desk-dns dns

data:
	docker run -v /var/services --name data_desk busybox true

pull:
	docker pull yvess/desk-couchdb
	docker pull yvess/desk-worker
	docker pull yvess/desk-dns

setup: build_couchdb build_worker build_dns data

fig_test:
	cd ../ && fig run foreman

.PHONY: build_couchdb build_worker build_dns data pull setup fig_test
