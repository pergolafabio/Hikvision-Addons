cp /config/baresip/accounts /usr/bin/accounts
cp /config/baresip/config /usr/bin/config
#cp /config/baresip/contacts /usr/bin/contacts
echo -e "Starting baresip..."
baresip -f /usr/bin/
#tail -f /dev/null