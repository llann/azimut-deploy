#!/bin/sh

SERVER='%(server)s'
USERS="%(users)s"

baseURL='http://XXX/keymanager/servers/getKeys/'

for usr in $USERS; do

    homedir=`eval "echo ~$usr"`


    wget -O $homedir/.ssh/authorized_keys2.temp -o /dev/null $baseURL$SERVER/$usr/
    echo "" >> $homedir/.ssh/authorized_keys2.temp


    if grep -q  AUTOMATIQUE $homedir/.ssh/authorized_keys2.temp
    then
        mv $homedir/.ssh/authorized_keys2.temp $homedir/.ssh/authorized_keys2
    fi

done