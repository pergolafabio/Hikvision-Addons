FROM debian:buster

USER root

# Set Environment Variables
ENV DEBIAN_FRONTEND=noninteractive
ARG OPENSIPS_VERSION=3.2
ARG OPENSIPS_BUILD=releases

#install basic components
RUN apt-get -y update -qq && apt-get -y install default-mysql-client sngrep gnupg2 m4 git nano sudo curl dbus apache2 lsb-release dirmngr apt-transport-https ca-certificates

RUN apt update && apt -y install php7.3 php7.3-gd php7.3-mysql php7.3-xmlrpc php-pear php7.3-cli php-apcu php7.3-curl php7.3-xml libapache2-mod-php7.3
RUN pear install MDB2#mysql
RUN sed -i "s#short_open_tag = Off#short_open_tag = On#g" /etc/php/7.3/apache2/php.ini

#RUN apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xF1656F24C74CD1D8
#RUN curl -sS https://downloads.mariadb.com/MariaDB/mariadb_repo_setup | sudo bash
#RUN apt update && apt -y install mariadb-server

#add keyserver, repository for opensips
RUN apt-key adv --fetch-keys https://apt.opensips.org/pubkey.gpg
RUN echo "deb https://apt.opensips.org buster ${OPENSIPS_VERSION}-${OPENSIPS_BUILD}" >/etc/apt/sources.list.d/opensips.list
RUN echo "deb https://apt.opensips.org focal cli-nightly" >/etc/apt/sources.list.d/opensips-cli.list

#install components (=3.2.5-1)
RUN apt-get -y update -qq && apt-get -y install opensips=3.2.5-1 opensips-cli opensips-mysql-module=3.2.5-1 opensips-postgres-module=3.2.5-1 opensips-unixodbc-module=3.2.5-1 opensips-jabber-module=3.2.5-1 opensips-cpl-module=3.2.5-1 opensips-radius-modules=3.2.5-1 opensips-presence-modules=3.2.5-1 opensips-xmlrpc-module=3.2.5-1 opensips-perl-modules=3.2.5-1 opensips-snmpstats-module=3.2.5-1 opensips-xmpp-module=3.2.5-1 opensips-carrierroute-module=3.2.5-1 opensips-berkeley-module=3.2.5-1 opensips-ldap-modules=3.2.5-1 opensips-geoip-module=3.2.5-1 opensips-regex-module=3.2.5-1 opensips-identity-module=3.2.5-1 opensips-b2bua-module=3.2.5-1 opensips-dbhttp-module=3.2.5-1 opensips-dialplan-module=3.2.5-1 opensips-http-modules=3.2.5-1 opensips-tls-module=3.2.5-1 opensips-cgrates-module=3.2.5-1
#RUN apt-get -y update -qq && apt-get -y install opensips opensips-cli opensips-mysql-module opensips-postgres-module opensips-unixodbc-module opensips-jabber-module opensips-cpl-module opensips-radius-modules opensips-presence-modules opensips-xmlrpc-module opensips-perl-modules opensips-snmpstats-module opensips-xmpp-module opensips-carrierroute-module opensips-berkeley-module opensips-ldap-modules opensips-geoip-module opensips-regex-module opensips-identity-module opensips-b2bua-module opensips-dbhttp-module opensips-dialplan-module opensips-http-modules opensips-tls-module opensips-cgrates-module
RUN git clone -b 8.3.2 https://github.com/OpenSIPS/opensips-cp.git /var/www/opensips-cp

#RUN service apache2 start \
#	&& mysql --password=opensipsrw -e "CREATE USER 'opensips'@'localhost' IDENTIFIED BY 'opensipsrw';" \
#	&& mysql --password=opensipsrw -e "GRANT ALL PRIVILEGES ON opensips.* TO 'opensips'@'localhost';" \
#	&& mysql --password=opensipsrw -e "FLUSH PRIVILEGES;" \
#	&& mysql --password=opensipsrw -e "CREATE DATABASE opensips;" \
#RUN mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/standard-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/standard-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/acc-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/alias_db-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/auth_db-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/avpops-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/clusterer-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/dialog-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/dialplan-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/dispatcher-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/domain-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/drouting-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/group-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/load_balancer-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/msilo-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/permissions-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/rtpproxy-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/rtpengine-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/speeddial-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/tls_mgm-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/usrloc-create.sql	 \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/presence-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /usr/share/opensips/mysql/registrant-create.sql \
#	&& mysql --host=homeassistant --user=opensips --password=opensipsrw opensips < /var/www/opensips-cp/config/db_schema.mysql

COPY apache2-opensips.conf /etc/apache2/sites-available/opensips.conf
COPY opensips.cfg /etc/opensips/opensips.cfg
COPY sql.sh /sql.sh
RUN chmod +x /sql.sh
COPY run.sh /run.sh
RUN chmod +x /run.sh

RUN a2dissite 000-default
RUN a2ensite opensips 
RUN chown -R www-data. /var/www/opensips-cp

#RUN service mariadb restart
#RUN service apache2 restart
EXPOSE 5060 5051

CMD ["/bin/bash", "/run.sh"]
