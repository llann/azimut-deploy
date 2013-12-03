from fabric.api import *

output.stdout = True

# Config
import config

env.key_filename = config.SSH_KEY


# Import server tools
import server

# Import owncloud deployement tools
import owncloud

# Import gestion deployement tools
import gestion

# Import zabbix tools
import zabbix
