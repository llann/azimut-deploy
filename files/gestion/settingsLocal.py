DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'gestion',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': 'gestion',
        'PASSWORD': '%(mysql_password)s',
        'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
    }
}


# Make this unique, and don't share it with anybody.
SECRET_KEY = '%(secret_key)s'

PROXMOX_USER = 'gestion_api@pam'
PROXMOX_PASS = '%(proxmox_pass)s'

VM_PASS_SECRET = '%(vm_password)s'

# List of key -> folder of git repositories
GIT_REPOS = {}

FABRIC_FOLDER = '/var/www/git-repo/azimut-deploy/'

GESTION_IP = '10.7.0.2'
GESTION_NAME = '%(gestion_name)s'
GESTION_VM_NAME = '%(gestion_vm_name)s'

GESTION_URL = 'http://%(gestion_name)s/'

BACKUP_SERVER = ''
BACKUP_BASE_FOLDER = ''

CREATEVM_DEFAULT_GROUPS = 'Servers'
CREATEVM_DEFAULT_GROUPS_ALLOWED = 'People,Server gestion'

SETUP_FABRIC_SCRIPT = 'server.setup'
COPY_USER_CONFIG_FABRIC_SCRIPT = 'server.copy_user_config'
UPDATE_KM_FABRIC_SCRIPT = 'server.copy_key_manager'
RUN_KM_FABRIC_SCRIPT = 'server.execute_key_manger'

SAMBA_SECRET_KEY = '%(samba_secret)s'

BROKER_URL = 'amqp://gestion:%(rabbitmq_password)s@127.0.0.1:5672/'

DEBUG = False
ALLOWED_HOSTS = ['%(gestion_name)s', '10.7.0.2']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format': '%%(asctime)s [%%(levelname)s] %%(name)s: %%(message)s'
        },

    },
    'handlers': {
        'default': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/apache2/django.log',
            'maxBytes': 1024*1024*50,  # 5 MB
            'backupCount': 5,
            'formatter': 'standard',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': False,
        },
        '': {
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.db.backends': {  # Stop SQL debug from logging to main logger
            'handlers': ['default'],
            'level': 'ERROR',
            'propagate': False
        },

    },

}

PROXMOX_IP_BASE = '10.7.0.'
