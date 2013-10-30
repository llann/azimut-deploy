from fabric.api import *
from fabric.contrib.files import upload_template

import time
import config


@task
def uname():
    """Execute uname"""
    run("uname -a")


@task
def upgrade():
    """Upgrade a sever"""
    sudo("apt-get update -y")
    sudo("apt-get upgrade -y")
    sudo("apt-get dist-upgrade -y")


@task
def install_sudo():
    """Install the sudo programm. Need to be runned with root"""
    run("apt-get update")
    run("apt-get install -y sudo")


@task
def reboot():
    """Reboot a machine"""
    x = 5
    while x > 0:
        print "Rebooting", env.host, "in", x, "seconds..."
        time.sleep(1)
        x -= 1
    sudo("reboot")


@task
def shutdown():
    """Shutdown a machine"""
    x = 5
    while x > 0:
        print "Shutdowning", env.host, "in", x, "seconds..."
        time.sleep(1)
        x -= 1
    sudo("halt")


@task
def copy_key_manager():
    """Copy the script for keymanagement [$AG:NeedKM]"""

    if not hasattr(env, 'keymanagerName') or env.keymanagerName == '':
        print "No keymanager name !"
        return

    upload_template('files/updateKeys.sh', '/root/updateKeys.sh', {
            'server': env.keymanagerName,
            'users': env.keyManagerUsers,
            'gestion_adresse': config.GESTION_ADDRESS,
        }, use_sudo=True)

    sudo("chmod +x /root/updateKeys.sh")


@task
def cron_key_manager():
    """Install the crontab for the keymanagement"""
    sudo('touch /tmp/crondump')
    with settings(warn_only=True):
        sudo('crontab -l > /tmp/crondump')
    sudo('echo " 42 * * * * /root/updateKeys.sh" >> /tmp/crondump')
    sudo('crontab /tmp/crondump')


@task
def setup_key_manager():
    """Setup the key manager [$AG:NeedKM]"""
    run('mkdir -p ~/.ssh/')
    sudo('apt-get install -y ca-certificates')
    copy_key_manager()
    cron_key_manager()
    execute_key_manger()


@task
def execute_key_manger():
    """Execute the keyManager"""
    sudo("/root/updateKeys.sh")


@task
def copy_config():
    """Copy config files"""

    put(config.AZIMUT_CONFIG + '/.vim*', '~')
    put(config.AZIMUT_CONFIG + '/.screenrc', '~')
    put(config.AZIMUT_CONFIG + '/.zshrc', '~')


@task
def copy_user_config():
    """Copy the config for a user [$AG:NeedUser]"""

    if not hasattr(env, 'fab_user') or env.fab_user == '':
        return

    put(config.AZIMUT_CONFIG + '/.vim*', '/home/' + env.fab_user + '/')
    put(config.AZIMUT_CONFIG + '/.screenrc', '/home/' + env.fab_user + '/')
    put(config.AZIMUT_CONFIG + '/.zshrc-user', '/home/' + env.fab_user + '/.zshrc')


@task
def install_base_progs():
    """Install base programms"""

    sudo('apt-get install -y zsh screen vim')


@task
def switch_shell_to_zsh():
    """Change the shell to ZSH"""
    run('chsh -s /bin/zsh')


@task
def install_rsync():
    """Install rsync"""
    sudo("apt-get install rsync")


@task
def add_gestion_for_self_vms():
    """Add a host for gestion vm so they can access the server even if on the same server [$AG:NeedGestion]"""

    if not hasattr(env, 'gestion_ip') or env.gestion_ip == '':
        return
    sudo('echo "' + env.gestion_ip + ' ' + env.gestion_name + '" >> /etc/hosts')


@task
def setup():
    """Setup a new server [$AG:NeedKM][$AG:NeedGestion]"""

    execute(install_sudo)
    execute(upgrade)
    execute(install_base_progs)
    execute(add_gestion_for_self_vms)
    execute(copy_config)
    execute(switch_shell_to_zsh)
    execute(install_rsync)

    if not hasattr(env, 'keymanagerName') or env.keymanagerName == '':
        prompt("Key manager name ?", 'keymanagerName')
        prompt("Key manager users ?", 'keyManagerUsers', 'root')

    execute(setup_key_manager)
