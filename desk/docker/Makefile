.PHONY:

worker_version=0.3.0
dns_version=0.3.0

default: build_worker build_dns

build_worker:
	cd worker; tar czvf etc.tar.gz etc; cd -
	docker buildx build \
		--load \
		--platform linux/amd64 \
		--build-arg BUILDKIT_INLINE_CACHE=1 \
		-t yvess/desk-worker:$(worker_version) \
		worker
	rm worker/etc.tar.gz

build_dns:
	cd dns; tar czvf etc.tar.gz -C ../worker etc -C ../dns etc; cd -
	docker buildx build \
		--load \
		--platform linux/amd64 \
		--build-arg BUILDKIT_INLINE_CACHE=1 \
		-t yvess/desk-dns:$(dns_version) \
		dns
	rm dns/etc.tar.gz

build: build_worker build_dns

push:
	docker push yvess/desk-worker:$(worker_version)
	docker push yvess/desk-dns:$(dns_version)

pull:
	docker pull yvess/desk-worker
	docker pull yvess/desk-dns
