#!/bin/bash
TABLE=domain
SQL_EXISTS=$(printf 'SHOW TABLES LIKE "%s"' "$TABLE")
USERNAME=opensips    
PASSWORD=opensipsrw
DATABASE=opensips

echo "Checking if tables exists ..."
if [[ $(mysql -h core-mariadb -u $USERNAME -p$PASSWORD -e "$SQL_EXISTS" $DATABASE) ]]
then
    echo "Table found in opensips db... skipping import"
else
    echo "Tables are being imported"
	/bin/bash /sql.sh
fi

# Change opensips socker HOSTIP
HOST_IP=$(ip route get 8.8.8.8 | head -n +1 | tr -s " " | cut -d " " -f 7)
echo Home assistant is running on: $HOST_IP
sed -i "s/socket=udp.*/socket=udp:${HOST_IP}:5060/g" /etc/opensips/opensips.cfg
sed -i "s/socket=tcp.*/socket=tcp:${HOST_IP}:5060/g" /etc/opensips/opensips.cfg

# change apache port from 80 to 5051 & database hostname to core-mariadb
sed -i "s/80*/5051/g" /etc/apache2/ports.conf
sed -i "s/localhost/core-mariadb/g" /var/www/opensips-cp/config/db.inc.php

/etc/init.d/apache2 restart
sleep 2
/usr/sbin/opensips -FE