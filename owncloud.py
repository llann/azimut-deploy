from fabric.api import *
from fabric.contrib.files import upload_template

#import time
#import config

@task
def setup_owncloud():
	"""Install a new owncloud server"""

	execute(setup_repo)
	execute(install)
	execute(configure_locale)
	execute(configure_apache)

@task
def setup_repo():
	"""Setup the owncloud repository"""

	sudo("echo 'deb http://download.opensuse.org/repositories/isv:ownCloud:community/Debian_7.0/ /' >> /etc/apt/sources.list.d/owncloud.list")
	sudo("wget http://download.opensuse.org/repositories/isv:ownCloud:community/Debian_7.0/Release.key -O - | apt-key add -")
	sudo("apt-get -y update")

@task
def install():
	"""Install the owncloud package and his depencencies"""
	sudo("apt-get -y install apache2 php5 php5-gd php-xml-parser php5-intl php5-mysql smbclient curl libcurl3 php5-curl owncloud")


@task
def configure_locale():
	"""Configure locales for VM without"""
	sudo("echo 'en_US.UTF-8 UTF-8' >> /etc/locale.gen")
	sudo("locale-gen")

@task
def configure_apache():
	"""Configure apache to work with owncloud"""

	# Disable default site
	sudo("a2dissite 000-default")

	# Enable needed apache modules
	sudo("a2enmod rewrite")
	sudo("a2enmod headers")
	sudo("a2enmod ssl")

	# Copy config
	put('files/owncloud/owncloud.conf', '/etc/apache2/sites-available/')

	# Enable site
	sudo("a2ensite owncloud.conf")

	# Restart apache
	sudo("service apache2 restart")