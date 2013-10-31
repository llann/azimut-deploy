azimut-deploy
=============

Azimut's fabric scripts. MIT license.

To be used with azimut-gestion tool !

## Setup

Copy `config.py.dist` to `config.py` and edit values if needed.

Some scripts except configuration files (for vim, zsh, etc.), who should be in the `AZIMUT_CONFIG` folder. You can find our files [here](https://github.com/Azimut-Prod/azimut-config).

## Scripts available

### server

The main task to setup a server is `server.setup`. You can execute special tasks, use `fab --list` for the full list.

`Zsh` is used for the default shell. The setup script try to install the keymanager, a tool from azimut-gestion. You can skip this part if you don't want to use it.

For all details, check documentation of azimut-gestion !

### owncloud

Can be used to quickly setup an owncloud server. Use `fab owncloud.setup_owncloud` to setup a new server. Sub tasks of the setup can be executed, use `fab --list` to get the full list.

### gestion

Can be used to quickly deploy the azimut-gestion tool. Use `fab gestion.setup` to setup a new server on a fresh proxmox installation. Use `fab gestion.update` to update code from azimut public repositories. Please read the documentation before using this tool :).