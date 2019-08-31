.PHONY:

worker_version=0.2.0
dns_version=0.2.0

default: build_worker build_dns

build_worker:
	cd worker; tar czvf etc.tar.gz etc; cd -
	docker build -t yvess/desk-worker:$(worker_version) worker
	rm worker/etc.tar.gz

build_dns:
	cd dns; tar czvf etc.tar.gz etc; cd -
	docker build -t yvess/desk-dns:$(dns_version) dns
	rm dns/etc.tar.gz

build: build_worker build_dns

pull:
	docker pull yvess/desk-worker
	docker pull yvess/desk-dns
