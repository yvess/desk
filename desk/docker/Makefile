default: build_couchdb build_worker build_dns

build_couchdb:
	docker build -t desk/couchdb couchdb

build_worker:
	docker build -t desk/worker worker

build_dns:
	docker build -t desk/dns dns

data:
	docker run -v /var/services --name data_desk busybox true

setup: build_couchdb build_worker build_dns data

fig_test:
	cd ../ && fig run foreman
