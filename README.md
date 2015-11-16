# FTPVista v4.0
FTPVista is an indexing and search engine for FTP servers on a local network.

## Installation
### Dependencies
FTPVista requires Python >=3.4 with few modules
```
sudo apt-get install python3 python3-pip uwsgi uwsgi-plugin-python3 python3-pycurl python3-sqlalchemy
```

And if using apache
```
sudo apt-get install libapache2-mod-proxy-uwsgi
sudo a2enmod proxy
sudo a2enmod proxy_uwsgi
```

Then, some pip dependencies
```
sudo pip3 install Whoosh scapy-python3 django pyftpdlib colorama
```

### Install
FTPVista includes an interactive installation script to ease the installation process.
```
python3 install.py install
```

The default installation process will:
  * create a specific user for FTPVista
  * install configuration files
  * install startup scripts (upstart or systemd)
  * install logrotate script

### Uninstall
FTPVista can uninstall itself through the _install.py_ script
```
python3 install.py uninstall
```

