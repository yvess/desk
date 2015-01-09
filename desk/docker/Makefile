default: build_couchdb build_worker build_dns

build_couchdb:
	docker build -t desk/couchdb couchdb

build_worker:
	docker build -t desk/worker worker

build_dns:
	docker build -t desk/dns dns
