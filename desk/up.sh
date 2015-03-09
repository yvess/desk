#!/bin/bash
BASEDIR=$(dirname $0)

trap "echo '* do cleanup';umount -f $BASEDIR/tmp/py27; fig kill && fig rm --force; kill 0" EXIT


# KILL & REMOVE ALL CONTAINER
fig kill && fig rm --force && fig up &

# WAIT FOR SSH FOR MOUNTING
until $(docker ps|egrep -q desk_ssh_1); do
  sleep 1
  echo "* waiting for desk_ssh_1"
done

# MOUNT SSHFS
echo "* sshfs mounting /var/py27"
sshfs root@$(echo $DOCKER_HOSTIP|cut -d ":" -f 2| sed -e "s#//##"):/var/py27 $BASEDIR/tmp/py27 -f -ovolname=py27desk -p 2025 -o auto_cache
