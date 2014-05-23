from fabric.api import *
from fabric.contrib.files import upload_template, append, comment

from StringIO import StringIO

import server

import uuid

import time
import socket

import pyproxmox

DEBIAN_TEMPLATE = "debian-7.0-standard_7.0-2_i386.tar.gz"
NGINX_IP = '10.7.0.1'
NGINX_NAME = 'nginx'
GESTION_IP = '10.7.0.2'
GESTION_NAME = 'gestion'

GIT_GESTION = 'https://github.com/llann/azimut-gestion.git'
GIT_DEPLOY = 'https://github.com/llann/azimut-deploy.git'
GIT_CONFIG = 'https://github.com/llann/azimut-config.git'


def gimme_prox_cox():
    """Return a proxmox connection"""

    return pyproxmox.pyproxmox(pyproxmox.prox_auth(env.server_ip, 'gestion_api@pam', env.gestion_password))


def wait_end_of_task(retour):
    """Wait for the end of a proxmox task"""
    if retour['data']:
        while True:
            status = gimme_prox_cox().getNodeTaskStatusByUPID(env.proxmox_node, retour['data'])
            if status['data']['status'] == 'running':
                time.sleep(1)
            else:
                return True
    return False


def create_vm(name, ip, disk, memory, swap, cpus):
    """Create a vm"""

    id = gimme_prox_cox().getClusterVmNextId()['data']

    post_data = {'ostemplate': env.storage + ':vztmpl/' + DEBIAN_TEMPLATE, 'vmid': id, 'cpus': cpus, 'description': 'Created from fabscript azimut-deploy/gestion',
                 'disk': disk, 'hostname': name, 'memory': memory,
                 'password': env.root_password, 'swap': swap, 'ip_address': ip}

    retour = gimme_prox_cox().createOpenvzContainer(env.proxmox_node, post_data)

    wait_end_of_task(retour)

    return id


def start_vm(id):
    """Start a vm"""

    retour = gimme_prox_cox().startOpenvzContainer(env.proxmox_node, id)

    wait_end_of_task(retour)


def get_proxmox_node():
    """Return the name of the proxmox node"""

    retour = gimme_prox_cox().getClusterStatus()

    if 'data' in retour and retour['data']:
        for info in retour['data']:
            if info['type'] == 'node':
                return info['name']


@task
def setup_proxmox():
    """Install a new proxmox server for gestion"""

    prompt("Root password ?", 'root_password')
    prompt("Server ip ?", 'server_ip')
    prompt("Server name ?", 'server_name', 'myproxmox.domain.com')
    prompt("Storage to use ?", 'storage', 'local')
    prompt("Main interface", 'interface', 'vmbr0')
    prompt("Do you want to add host entry to main server on gestion VM ?", 'addhostongestion', 'yes')

    env.password = env.root_password
    env.gestion_password = str(uuid.uuid4())
    env.rabbitmq_password = str(uuid.uuid4())
    env.mysql_password = str(uuid.uuid4())

    execute(server.install_sudo)
    execute(server.upgrade)
    execute(disable_proxmox_repo)
    execute(add_gestion_user)
    execute(setup_networking)

    execute(reboot)

    # Let's find the proxmox node name
    env.proxmox_node = get_proxmox_node()

    if not env.proxmox_node:
        print "Cannot get the proxmox node :("
    else:
        print "Proxmox node is", env.proxmox_node

    execute(download_debian_template)
    execute(deploy_and_setup_nginx)
    execute(deploy_and_setup_gestion)
    execute(add_initial_gestion_data)

    execute(post_setup_ngnix)
    execute(post_setup_gestion)
    execute(post_setup)


@task
def reboot():
    """Reboot the machine and wait for it to be up again"""
    sudo('reboot')
    execute(check_if_down)
    execute(check_if_alive)
    time.sleep(15)


@task
def disable_proxmox_repo():
    """Disable the proxmox entreprise repo"""

    comment('/etc/apt/sources.list.d/pve-enterprise.list', "deb")


@task
def add_gestion_user():
    """Add the user for gestion"""

    env.gestion_password = str(uuid.uuid4())

    # Create system user
    sudo("useradd -m gestion_api")

    # Change his password
    sudo('echo \'gestion_api:' + env.gestion_password + '\' | chpasswd')

    # Create user inside proxmox
    sudo("pveum useradd gestion_api@pam -comment 'Gestion API user'")

    # Grand admin rights
    sudo("pveum aclmod / -user gestion_api@pam -role Administrator")


@task
def setup_networking():
    """Setup networking"""

    upload_template('files/gestion/nat-vz', '/etc/init.d/nat-vz',  {
        'server_ip': env.server_ip,
        'interface': env.interface,
    })

    sudo('chmod 755 /etc/init.d/nat-vz')
    sudo('service nat-vz start')
    sudo('update-rc.d nat-vz defaults')


@task
def download_debian_template():
    """Download the debian template"""

    post_data = {'storage': env.storage, 'template': DEBIAN_TEMPLATE}

    retour = gimme_prox_cox().connect('post', "nodes/%s/aplinfo" % (env.proxmox_node,), post_data)

    wait_end_of_task(retour)


@task
def check_if_alive(port=22):
    """Wait until an host is alive"""
    coxOk = False

    if '@' in env.host:
        zeHost = env.host.split('@')[1]
    else:
        zeHost = env.host

    if ':' in zeHost:
        zeHost, port = zeHost.split(':')

    while not coxOk:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((zeHost, port))
            s.close()
            coxOk = True
        except Exception:
            time.sleep(1)


@task
def check_if_down(port=22):
    """Wait until an host is down"""
    coxOk = False

    if '@' in env.host:
        zeHost = env.host.split('@')[1]
    else:
        zeHost = env.host

    if ':' in zeHost:
        zeHost, port = zeHost.split(':')

    while not coxOk:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((zeHost, port))
            s.close()
            time.sleep(1)
        except Exception:
            coxOk = True


@task
def deploy_and_setup_nginx():
    """Deploy and setup the nginx vm"""

    execute(deploy_nginx)
    env.nginx_vm_id = '100'

    # Swith to nginx VM
    backup_hosts = env.hosts
    env.hosts = ['root@' + env.server_ip + ':10122']

    execute(check_if_alive, port=10122)
    execute(server.install_sudo)
    execute(server.upgrade)
    execute(install_nginx)
    execute(configure_nginx)

    env.hosts = backup_hosts


@task
def install_nginx():
    """Install nginx"""
    sudo('apt-get -y install nginx')


@task
def configure_nginx():
    """Configure nginx"""
    sudo('rm /etc/nginx/sites-enabled/default')

    upload_template('files/gestion/ngnix.conf', '/etc/nginx/sites-available/ngnix.conf',  {
        'gestion_hostname': GESTION_NAME + '.' + env.server_name,
    })

    sudo('ln -s /etc/nginx/sites-available/ngnix.conf /etc/nginx/sites-enabled/ngnix.conf')
    sudo('service nginx restart')


@task
def deploy_nginx():
    """Deploy the nginx vm"""

    env.nginx_vm_id = create_vm(NGINX_NAME, NGINX_IP, 10, 512, 0, 1)
    start_vm(env.nginx_vm_id)


@task
def deploy_and_setup_gestion():
    """Deploy and setup the gestion vm"""

    execute(deploy_gestion)
    env.gestion_vm_id = '101'

    # Switch to gestion VM
    backup_hosts = env.hosts
    env.hosts = ['root@' + env.server_ip + ':10222']

    execute(check_if_alive, port=10222)
    execute(server.install_sudo)
    execute(server.upgrade)
    execute(install_apache)
    execute(configure_apache)
    execute(install_rabbitmq)
    execute(configure_rabbitmq)
    execute(install_mysql)
    execute(configure_mysql)
    execute(install_python)
    execute(install_git)
    execute(clone_repos)
    execute(install_pip_dep)
    execute(install_supervisor)
    execute(configure_gestion)
    execute(configure_deploy)
    execute(chmod_and_chown)
    execute(sync_databases)
    execute(move_www_home)
    execute(generate_www_ssh_key)
    execute(configure_ssh)
    if env.addhostongestion == 'yes':
        execute(add_mainvm_to_hosts)
    execute(start_celery)
    execute(restart_apache)

    env.hosts = backup_hosts


@task
def move_www_home():
    """Move home of www-data to /home"""
    sudo("mkdir /home/www-data")
    sudo("chown www-data:www-data /home/www-data")
    sudo("service apache2 stop")
    sudo("usermod -d /home/www-data www-data")
    sudo("service apache2 start")


@task
def generate_www_ssh_key():
    """Genate a ssh-key for www-data"""
    sudo("su www-data -c 'ssh-keygen -f /home/www-data/.ssh/id_rsa -t rsa -N \"\"'")


@task
def configure_ssh():
    upload_template('files/gestion/config', '/home/www-data/.ssh/config')
    sudo("chown www-data:www-data /home/www-data/.ssh/config")


@task
def deploy_gestion():
    """Deploy the gestion vm"""

    env.gestion_vm_id = create_vm(GESTION_NAME, GESTION_IP, 20, 1024, 0, 2)
    start_vm(env.gestion_vm_id)


@task
def install_apache():
    """Install apache"""
    sudo('apt-get -y install apache2 libapache2-mod-wsgi')


@task
def configure_apache():
    """Configure apache"""
    # Disable default site
    sudo('a2dissite 000-default')

    # Copy config
    upload_template('files/gestion/apache.conf', '/etc/apache2/sites-available/apache.conf',  {})

    # Enable config
    sudo('a2ensite apache.conf', pty=True)


@task
def restart_apache():
    """Restart apache"""
    sudo('service apache2 restart')


@task
def install_rabbitmq():
    """Install rabbitmq"""
    sudo('apt-get -y install rabbitmq-server')


@task
def configure_rabbitmq():
    """Configure rabbitmq"""

    #Enable webpluging
    sudo('rabbitmq-plugins enable rabbitmq_management')

    #Setup admin user
    sudo('rabbitmqctl add_user admin ' + env.root_password)
    sudo('rabbitmqctl set_user_tags admin administrator')
    sudo('rabbitmqctl set_permissions admin .\* .\* .\*')

    #Setup gestion user
    sudo('rabbitmqctl add_user gestion ' + env.rabbitmq_password)
    sudo('rabbitmqctl set_permissions gestion .\* .\* .\*')

    #Disable guest user
    sudo('rabbitmqctl delete_user guest')

    #Restart rabbitmq
    sudo('service rabbitmq-server restart')


@task
def install_mysql():
    """Install mysql"""

    # First, setup root password
    sudo('apt-get install -y debconf-utils')

    debconf_defaults = [
        "mysql-server-5.5 mysql-server/root_password_again password %s" % (env.root_password,),
        "mysql-server-5.5 mysql-server/root_password password %s" % (env.root_password,),
    ]

    sudo("echo '%s' | debconf-set-selections" % "\n".join(debconf_defaults))

    sudo("apt-get -y install mysql-server")


@task
def configure_mysql():
    """Configure mysql"""

    def mysql_execute(sql):
        """Executes passed sql command using mysql shell."""

        sql = sql.replace('"', r'\"')
        return run('echo "%s" | mysql --user="root" --password="%s"' % (sql, env.root_password))

    mysql_execute("CREATE DATABASE gestion DEFAULT CHARACTER SET utf8 DEFAULT COLLATE utf8_general_ci;")
    mysql_execute("CREATE USER 'gestion'@'localhost' IDENTIFIED BY '%s';" % (env.mysql_password,))
    mysql_execute("GRANT ALL ON gestion.* TO 'gestion'@'localhost'; FLUSH PRIVILEGES;")


@task
def install_python():
    """Install python and python deps"""
    sudo('apt-get install -y python-crypto python-mysqldb python-imaging python-pip python')


@task
def install_git():
    """Install git"""
    sudo('apt-get install -y git')


@task
def clone_repos():
    """Clone the gestion, config and deploy repository"""

    sudo('mkdir -p /var/www/git-repo')

    with cd('/var/www/git-repo'):
        sudo('git clone ' + GIT_GESTION + ' azimut-gestion')
        sudo('git clone ' + GIT_CONFIG + ' azimut-config')
        sudo('git clone ' + GIT_DEPLOY + ' azimut-deploy')


@task
def pull_repos():
    """Pull the gestion, config and deploy repository"""

    sudo('mkdir -p /var/www/git-repo')

    with cd('/var/www/git-repo'):
        with cd('azimut-gestion'):
            sudo('git pull')
        with cd('azimut-config'):
            sudo('git pull')
        with cd('azimut-deploy'):
            sudo('git pull')


@task
def install_pip_dep():
    """Install python depenencies using pip"""

    sudo('pip install -r /var/www/git-repo/azimut-gestion/doc/pip-reqs.txt')


@task
def install_supervisor():
    """Install supervisor"""
    sudo('apt-get install -y supervisor')


@task
def chmod_and_chown():
    """Update folder rights"""
    with cd('/var/www/git-repo'):
        sudo("chown -R www-data:www-data .")

    with cd('/var/log/apache2/'):
        sudo('chown www-data:www-data .')
        sudo('touch django.log')
        sudo("chmod 777 *")


@task
def sync_databases():
    """Sync django databases"""
    with cd('/var/www/git-repo/azimut-gestion'):
        sudo("python manage.py syncdb --noinput")
        sudo("python manage.py migrate --noinput")


@task
def start_celery():
    """Start celery deamon"""
    with cd('/var/www/git-repo/azimut-gestion'):
        sudo('su www-data -c "supervisord -c data/supervisord.conf"')


@task
def stop_celery():
    """Stop celery deamon"""
    with cd('/var/www/git-repo/azimut-gestion'):
        sudo('su www-data -c "supervisorctl -c data/supervisord.conf shutdown"')


@task
def configure_deploy():
    """Config deploy scripts"""

    upload_template('files/gestion/config.py', '/var/www/git-repo/azimut-deploy/config.py',  {
        'gestion': GESTION_NAME + '.' + env.server_name,
    })


@task
def configure_gestion():
    """Configure the djagno application"""
    upload_template('files/gestion/settingsLocal.py', '/var/www/git-repo/azimut-gestion/app/settingsLocal.py',  {
        'mysql_password': env.mysql_password,
        'secret_key': str(uuid.uuid4()),
        'proxmox_pass': env.gestion_password,
        'vm_password': str(uuid.uuid4()),
        'gestion_name': GESTION_NAME + '.' + env.server_name,
        'gestion_vm_name': env.server_name,
        'samba_secret': str(uuid.uuid4()),
        'rabbitmq_password': env.rabbitmq_password
        })


@task
def add_initial_gestion_data():
    """Add default data: users, servers, groups, port fowarded"""

    def do_command(command):
        """Execute a command inside django shell"""
        command = command.replace('"', r'\"')
        with cd('/var/www/git-repo/azimut-gestion'):
            sudo('echo "%s" | python manage.py shell' % (command,))

    backup_hosts = env.hosts
    env.hosts = ['root@' + env.server_ip + ':10222']

    @task
    def add_initial_gestion_data_on_server():
        # Groups

        do_command("from groups.models import Group; Group(name='Servers').save()")
        do_command("from groups.models import Group; Group(name='People').save()")
        do_command("from groups.models import Group; Group(name='Server gestion').save()")

        # Admin user
        do_command("from django.contrib.auth.models import User; user = User.objects.create_user('admin', 'admin@" + env.server_name + "', '" + env.root_password + "'); user.is_staff = True; user.is_superuser = True; user.save()")
        do_command("from django.contrib.auth.models import User; from groups.models import Group; people = Group.objects.get(name='People'); user = User.objects.get(username='admin'); people.users.add(user); people.save()")

        # Add servers
        load_groups = "from groups.models import Group; servers = Group.objects.get(name='Servers'); people = Group.objects.get(name='People'); gestion = Group.objects.get(name='Server gestion');"
        add_srv_to_groups = " servers.servers.add(server); people.allowed_servers.add(server); gestion.allowed_servers.add(server);"
        add_root_user = " from servers.models import ServerUser; ServerUser(server=server, name='root').save();"

        do_command(load_groups + "from servers.models import Server; server = Server(name='%s', keymanger_name='%s', is_vm=False, external_ip='%s', ssh_connection_string_from_gestion='root@%s', ssh_connection_string_from_backup='root@%s', external_interface='%s', is_proxmox=True, proxmox_node_name='%s', samba_management=False); server.save(); " % (env.server_name, env.server_name, env.server_ip, env.server_name, env.server_name, env.interface, env.proxmox_node) + add_srv_to_groups + add_root_user)

        do_command(load_groups + "from servers.models import Server; mainsrv = Server.objects.get(name='%s'); server = Server(name='ngnix.%s', keymanger_name='ngnix.%s', is_vm=True, internal_ip='10.7.0.1', ssh_connection_string_from_gestion='root@10.7.0.1', ssh_connection_string_from_backup='-p 10122 root@%s', is_proxmox=False, samba_management=False, vm_host=mainsrv); server.save(); mainsrv.ngnix_server = server; mainsrv.save(); " % (env.server_name, env.server_name, env.server_name, env.server_name) + add_srv_to_groups + add_root_user)

        do_command(load_groups + "from servers.models import Server; mainsrv = Server.objects.get(name='%s'); server = Server(name='gestion.%s', keymanger_name='gestion.%s', is_vm=True, internal_ip='10.7.0.2', ssh_connection_string_from_gestion='root@10.7.0.2', ssh_connection_string_from_backup='-p 10222 root@%s', is_proxmox=False, samba_management=False, vm_host=mainsrv); server.save(); " % (env.server_name, env.server_name, env.server_name, env.server_name) + add_srv_to_groups + add_root_user + " gestion.servers.add(server);")

        # Host name forwarding
        load_servers = "from servers.models import Server; mainsrv = Server.objects.get(name='%s'); ngnixsrv = Server.objects.get(name='ngnix.%s'); gestionsrv = Server.objects.get(name='gestion.%s'); " % (env.server_name, env.server_name, env.server_name)
        base_hostname = load_servers + "from hostnameforwarding.models import Hostnameforwarded;"
        do_command(base_hostname + " Hostnameforwarded(server_host=mainsrv, server_to=gestionsrv, domain='gestion.%s').save()" % (env.server_name,))

        # Portforwarding
        base_portforwarding = load_servers + "from portforwarding.models import Portforwarded;"
        do_command(base_portforwarding + " Portforwarded(server_host=mainsrv, server_to=ngnixsrv, port_from=80, port_to=80, protocol='tcp').save()")
        do_command(base_portforwarding + " Portforwarded(server_host=mainsrv, server_to=ngnixsrv, port_from=10122, port_to=22, protocol='tcp').save()")
        do_command(base_portforwarding + " Portforwarded(server_host=mainsrv, server_to=gestionsrv, port_from=10222, port_to=22, protocol='tcp').save()")

        # Ssh keys
        fd = StringIO()
        get('/home/www-data/.ssh/id_rsa.pub', fd)
        public_key = fd.getvalue().strip()

        do_command("from servers.models import Server, SshKey; gestionsrv = Server.objects.get(name='gestion.%s'); SshKey(server=gestionsrv, user='www-data', key='%s').save();" % (env.server_name, public_key))

    execute(add_initial_gestion_data_on_server)

    env.hosts = backup_hosts


@task
def post_setup_ngnix():
    """Setup nginx server using standard script to have keymanager and default config"""

    # Swith to nginx VM
    backup_hosts = env.hosts
    env.hosts = ['root@' + env.server_ip + ':10122']

    env.keymanagerName = 'ngnix.' + env.server_name
    env.keyManagerUsers = 'root'
    env.gestion_ip = '10.7.0.2'
    env.gestion_name = 'gestion.' + env.server_name

    execute(server.setup)

    env.hosts = backup_hosts


@task
def post_setup_gestion():
    """Setup gestion server using standard script to have keymanager and default config"""

    # Swith to nginx VM
    backup_hosts = env.hosts
    env.hosts = ['root@' + env.server_ip + ':10222']

    env.keymanagerName = 'gestion.' + env.server_name
    env.keyManagerUsers = 'root'
    env.gestion_ip = '10.7.0.2'
    env.gestion_name = 'gestion.' + env.server_name

    execute(server.setup)

    env.hosts = backup_hosts


@task
def post_setup():
    """Setup main server using standard script to have keymanager and default config"""

    env.keymanagerName = env.server_name
    env.keyManagerUsers = 'root'
    env.gestion_ip = '10.7.0.2'
    env.gestion_name = 'gestion.' + env.server_name

    execute(server.setup)


@task
def update_code():
    """Update code"""

    backup_hosts = env.hosts

    env.hosts = ['root@' + env.hosts[0].split('@')[-1] + ':10222']

    execute(stop_celery)
    execute(pull_repos)
    execute(chmod_and_chown)
    execute(sync_databases)
    execute(restart_apache)
    execute(start_celery)

    env.hosts = backup_hosts


@task
def add_mainvm_to_hosts():
    """Add main VM to hosts"""
    append('/etc/hosts', env.server_ip + ' ' + env.server_name, use_sudo=True)
