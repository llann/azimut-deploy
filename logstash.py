from fabric.api import *
from fabric.contrib.files import append, comment, upload_template
import config

@task
def setup_logstash_agent():
    """Setup the logstash agent [$AG:NeedKM]"""
    execute(install_jre_and_supervisor)
    execute(create_dir)
    execute(download_logstash)
    execute(configure_supervisor)
    execute(install_crontab)
    execute(start_supervisor)
    execute(download_config)
    execute(start_logstash)


@task
def install_jre_and_supervisor():
    """Install jre and supervisor"""
    sudo('apt-get install -y openjdk-6-jre supervisor')


@task
def create_dir():
    """Create logstash dir"""
    sudo('mkdir /opt/logstash/')


@task
def download_logstash():
    with cd('/opt/logstash'):
        sudo('wget https://download.elasticsearch.org/logstash/logstash/logstash-1.2.2-flatjar.jar -O logstash.jar')


@task
def configure_supervisor():
    """Configure supervisor [$AG:NeedKM]"""

    if not hasattr(env, 'keymanagerName') or env.keymanagerName == '':
        print "No keymanager name !"
        return

    upload_template('files/logstash/supervisor.conf', '/opt/logstash/supervisor.conf', {'server_name': env.keymanagerName, 'gestion_name': config.GESTION_ADDRESS})


@task
def install_crontab():
    """Install crontab"""

    sudo('touch /tmp/crondump')
    with settings(warn_only=True):
        sudo('crontab -l > /tmp/crondump')

    append('/tmp/crondump', '42 * * * * cd /opt/logstash && supervisorctl -c supervisor.conf start updateconf', use_sudo=True)
    append('/tmp/crondump', '45 * * * * cd /opt/logstash && supervisorctl -c supervisor.conf restart logstash', use_sudo=True)
    sudo('crontab /tmp/crondump')


@task
def download_config():
    """Download config"""

    with cd('/opt/logstash'):
        sudo('supervisorctl -c supervisor.conf start updateconf')


@task
def start_supervisor():
    """Start supervisor"""

    with cd('/opt/logstash'):
        sudo("supervisord -c supervisor.conf")


@task
def start_logstash():
    """Start logstash"""

    with cd('/opt/logstash'):
        sudo('supervisorctl -c supervisor.conf start logstash')
