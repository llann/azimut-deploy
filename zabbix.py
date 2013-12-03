from fabric.api import *
from fabric.contrib.files import append, comment

import config

import server


@task
def setup_zabbix_agent():
    """Setup the zabbix agent"""
    execute(setup_zabbix_repos)
    execute(install_zabbix_agent)
    execute(configure_zabbix_agent)
    execute(restart_zabbix_agent)

@task
def setup_zabbix_repos():
    """Setup zabbix repos"""

    sudo("wget http://repo.zabbix.com/zabbix/2.2/debian/pool/main/z/zabbix-release/zabbix-release_2.2-1+wheezy_all.deb -O /tmp/zabbix.deb")
    sudo("dpkg -i /tmp/zabbix.deb")
    sudo("apt-get update")

@task
def install_zabbix_agent():
    """Install zabbix agent"""
    sudo("apt-get install zabbix-agent")


@task
def configure_zabbix_agent():
    """Configure zabbix agent"""
    append('/etc/zabbix/zabbix_agentd.conf', 'Server=' + config.ZABBIX_SERVER)
    append('/etc/zabbix/zabbix_agentd.conf', 'ServerActive=' + config.ZABBIX_SERVER)
    #append('/etc/zabbix/zabbix_agentd.conf', 'Hostname=')
    comment('/etc/zabbix/zabbix_agentd.conf', 'Server=127.0.0.1')



@task
def restart_zabbix_agent():
    """Restat zabbx agent"""
    sudo("service zabbix-agent restart")