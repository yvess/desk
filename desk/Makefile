# do nothing on default
default:

# PIP

# save current requirements
freeze:
	pip freeze -r /tmp/requirements.txt > /tmp/requirements.txt
	sed -i "s/-e git+https:\/\/github.com\/yvess\/desk.git/\#-e git+https:\/\/github.com\/yvess\/desk.git/" /tmp/requirements.txt
	egrep "##|lxml" /tmp/requirements.txt > /tmp/requirements_new.txt
	egrep "##|lxml" /tmp/requirements.txt -v >> /tmp/requirements_new.txt
	rm /tmp/requirements.txt && mv /tmp/requirements_new.txt /tmp/requirements.txt
	cp /tmp/requirements.txt images/dns/requirements.txt
	cp /tmp/requirements.txt images/master/requirements.txt

images:
	cd images/foreman && docker build -t yvess/desk_foreman . && cd - &
	cd images/dns && docker build -t yvess/desk_dns . && cd -

stop_worker:
	s6-svc -d /var/run/s6/services/worker

start_worker:
	s6-svc -d /var/run/s6/services/worker

start_worker_fg:
	./dworker run -v

play:
	docker run -it --rm --volumes-from=projects -w /projects/desk/desk/images/playbooks \
	-v /mnt/sda1/projects/desk/desk/images/ansible-master/etc/ansible/hosts:/etc/ansible/hosts \
	--link desk_cdb_1:cdb_1 --link desk_foreman_1:foreman_1 --link desk_dnsa_1:dnsa_1 --link desk_dnsb_1:dnsb_1 \
	yvess/ansible-master

play-dns:
	docker run -it --rm --volumes-from=projects -w /projects/desk/desk/images/playbooks \
	-v /mnt/sda1/projects/desk/desk/images/ansible-master/etc/ansible/hosts:/etc/ansible/hosts \
	--link desk_cdb_1:cdb_1 --link desk_foreman_1:foreman_1 --link desk_dnsa_1:dnsa_1 --link desk_dnsb_1:dnsb_1 \
	-h ansible yvess/ansible-master dnsservers.yml

play-testdata:
	docker run -it --rm --volumes-from=projects -w /projects/desk/desk/images/playbooks \
	-v /mnt/sda1/projects/desk/desk/images/ansible-master/etc/ansible/hosts:/etc/ansible/hosts \
	--link desk_cdb_1:cdb_1 --link desk_foreman_1:foreman_1 --link desk_dnsa_1:dnsa_1 --link desk_dnsb_1:dnsb_1 \
	-h ansible yvess/ansible-master parts/couchdb-testdata.yml

enter-ansible:
	docker run -it --rm --volumes-from=projects -w /projects/desk/desk/images/playbooks \
	-v /mnt/sda1/projects/desk/desk/images/ansible-master/etc/ansible/hosts:/etc/ansible/hosts \
	--link desk_cdb_1:cdb_1 --link desk_foreman_1:foreman_1 --link desk_dnsa_1:dnsa_1 --link desk_dnsb_1:dnsb_1 \
	-h ansible --entrypoint bash yvess/ansible-master

up:
	docker-compose -f docker-compose.yml -f docker-extra.yml up -d
