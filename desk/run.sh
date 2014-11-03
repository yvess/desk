#!/bin/bash
trap 'kill 0' SIGINT SIGTERM EXIT
docker exec -it desk_foreman_1 bash -c "cd /projects/desk/desk && . /var/py27/bin/activate && ./dworker run" &
docker exec -it desk_dnsa_1 bash -c "cd /projects/desk/desk && . /var/py27/bin/activate && ./dworker run" &
docker exec -it desk_dnsb_1 bash -c "cd /projects/desk/desk && . /var/py27/bin/activate && ./dworker run"
