#!/usr/bin/env python3

import os
import argparse
import subprocess
import configparser


def _command_exists(command):
    return subprocess.call(["which", command]) == 0


def init_config(args):
    config = configparser.SafeConfigParser()
    config.read(args.config_file)
    return config


def _q(text):
    result = input("%s [y/N] " % text)
    return result.upper() == 'Y'


def uninstall_services(args):
    if args.service == 'upstart':
        if _q('Delete /etc/init/ftpvista.conf and /etc/init/ftpvista-oc.conf ?'):
            os.remove('/etc/init/ftpvista.conf')
            os.remove('/etc/init/ftpvista-oc.conf')
            print("Files successfully deleted")
    elif args.service == 'systemd':
        if _q('Delete /etc/systemd/system/ftpvista.service and /etc/systemd/system/ftpvista-oc.service ?'):
            print("Disabling services via systemctl")
            subprocess.call(["systemctl", "disable", "ftpvista"])
            subprocess.call(["systemctl", "disable", "ftpvista-oc"])
            os.remove('/etc/systemd/system/ftpvista.service')
            os.remove('/etc/systemd/system/ftpvista-oc.service')
            print("Files successfully deleted")
    return 0


def install_services(args):
    fupstart = """description "{description}"
author "joel.charles91@gmail.com"

start on runlevel [2345]
stop on runlevel [!2345]

chdir {chdir}
exec {chdir}/ftpvista.py --config "{chdir}/ftpvista.conf" {start}
"""
    fsystemd = """[Unit]
Description={description}

After=network.target

[Service]
WorkingDirectory={chdir}
ExecStart={chdir}/ftpvista.py --config "{chdir}/ftpvista.conf" {start}

[Install]
WantedBy=multi-user.target
"""
    dirname = os.path.dirname(os.path.realpath(__file__))
    if args.service == 'upstart':
        if _q('2 new files will be created: /etc/init/ftpvista.conf and /etc/init/ftpvista-oc.conf. Continue ?'):
            with open('/etc/init/ftpvista.conf', 'w') as ws:
                ws.write(fupstart.format(chdir=dirname, start='start', description='FTPVista'))
            with open('/etc/init/ftpvista-oc.conf', 'w') as ws:
                ws.write(fupstart.format(chdir=dirname, start='start-oc', description='FTPVista online checker'))
            print("Files successfully installed")
    elif args.service == 'systemd':
        if _q('2 new files will be created: /etc/systemd/system/ftpvista.service and /etc/systemd/system/ftpvista-oc.service. Continue ?'):
            with open('/etc/systemd/system/ftpvista.service', 'w') as ws:
                ws.write(fsystemd.format(chdir=dirname, start='start', description='FTPVista'))
            with open('/etc/init/ftpvista-oc.conf', 'w') as ws:
                ws.write(fsystemd.format(chdir=dirname, start='start-oc', description='FTPVista online checker'))
            print("Enabling services via systemctl")
            subprocess.call(["systemctl", "enable", "ftpvista"])
            subprocess.call(["systemctl", "enable", "ftpvista-oc"])
            print("Files successfully installed")
    return 0


def uninstall_logrotate(args):
    if _q('/etc/logrotate.d/ftpvista will be deleted. Continue ?'):
        os.remove('/etc/logrotate.d/ftpvista')
        print("File successfully deleted")
    return 0


def install_logrotate(args):
    if not _command_exists('logrotate'):
        print("logrotate doesn't seems to be intalled. Skipping.")
        return 1
    flogrotate = """{folder}/* {
  rotate 0
  copytruncate
  size 10M
  missingok
  notifempty
}
"""
    config = init_config(args)
    if _q('/etc/logrotate.d/ftpvista will be created. Continue ?'):
        with open('/etc/logrotate.d/ftpvista', 'w') as ws:
            ws.write(flogrotate.format(folder=config.get('logs', 'folder')))
    return 0


def init():
    dirname = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="FTPVista 4.0 installer")
    parser.add_argument("-c", "--config", dest="config_file", metavar="FILE", default=os.path.join(dirname, 'ftpvista.conf'), help="Path to the config file")
    subparsers = parser.add_subparsers(dest='action')
    # install
    parser_install = subparsers.add_parser('install', help='Install FTPVista system elements')
    subparsers_install = parser_install.add_subparsers(dest='install_action')
    # install services
    parser_services = subparsers_install.add_parser('services', help='Generate and install services scripts for upstart or systemd', func=install_services)
    parser_services.add_argument("service", choices=["upstart", "systemd"])
    # install logrotate
    subparsers_install.add_parser('logrotate', help='Generate and install logrotate specific configuration for FTPVista', func=install_logrotate)
    # uninstall
    parser_uninstall = subparsers.add_parser('uninstall', help='Uninstall FTPVista system elements')
    subparsers_uninstall = parser_uninstall.add_subparsers(dest='uninstall_action')
    # uninstall services
    parser_services = subparsers_uninstall.add_parser('services', help='Uninstall services scripts of upstart or systemd', func=uninstall_services)
    parser_services.add_argument("service", choices=["upstart", "systemd"])
    # uninstall logrotate
    subparsers_uninstall.add_parser('logrotate', help='Uninstall logrotate specific configuration of FTPVista', func=uninstall_logrotate)

    args = parser.parse_args()

    if os.getuid() != 0:
        print("You must be root in order to run FTPVista installer. Exiting.")
        exit(1)

    return args.func(args)

if __name__ == '__main__':
    init()
