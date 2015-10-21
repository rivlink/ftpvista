#!/usr/bin/env python3

import os
import re
import argparse
import subprocess
import configparser


def _stat_proc1exe():
    regex = re.compile("^.* -> .(.*).$")
    out = subprocess.check_output(["stat", "--format", "%N", "/proc/1/exe"]).decode().strip()
    matches = regex.match(out)
    return matches.group(1)


def _command_exists(command):
    with open(os.devnull, "w") as f:
        return subprocess.call(["which", command], stdout=f) == 0
    return False


def init_config(args):
    config = configparser.SafeConfigParser()
    config.read(args.config_file)
    return config


def _q(text):
    result = input("%s [y/N] " % text)
    return result.upper() == 'Y'


def uninstall_services(args):
    if not hasattr(args, 'service') or args.service == 'upstart':
        if os.path.isfile('/etc/init/ftpvista.conf') or os.path.isfile('/etc/init/ftpvista-oc.conf'):
            if _q('Delete /etc/init/ftpvista.conf and /etc/init/ftpvista-oc.conf ?'):
                os.remove('/etc/init/ftpvista.conf')
                os.remove('/etc/init/ftpvista-oc.conf')
                print("Files successfully deleted")
        else:
            print('Nothing to delete for service upstart.')
    elif not hasattr(args, 'service') or args.service == 'systemd':
        if os.path.isfile('/etc/systemd/system/ftpvista.service') or os.path.isfile('/etc/systemd/system/ftpvista-oc.service'):
            if _q('Delete /etc/systemd/system/ftpvista.service and /etc/systemd/system/ftpvista-oc.service ?'):
                print("Disabling services via systemctl")
                subprocess.call(["systemctl", "disable", "ftpvista"])
                subprocess.call(["systemctl", "disable", "ftpvista-oc"])
                os.remove('/etc/systemd/system/ftpvista.service')
                os.remove('/etc/systemd/system/ftpvista-oc.service')
                print("Files successfully deleted")
        else:
            print('Nothing to delete for service systemd.')
    return 0


def install_services(args):
    print('-- Services installation --')
    if not hasattr(args, 'service'):
        if '/systemd' in _stat_proc1exe():
            print('No service specified. Assuming systemd.')
            args.service = 'systemd'
        else:
            print('No service specified. Assuming upstart.')
            args.service = 'upstart'

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
    if args.service == 'systemd':
        if _q('2 new files will be created: /etc/systemd/system/ftpvista.service and /etc/systemd/system/ftpvista-oc.service. Continue ?'):
            with open('/etc/systemd/system/ftpvista.service', 'w') as ws:
                ws.write(fsystemd.format(chdir=dirname, start='start', description='FTPVista'))
            with open('/etc/init/ftpvista-oc.conf', 'w') as ws:
                ws.write(fsystemd.format(chdir=dirname, start='start-oc', description='FTPVista online checker'))
            print("Enabling services via systemctl")
            subprocess.call(["systemctl", "enable", "ftpvista"])
            subprocess.call(["systemctl", "enable", "ftpvista-oc"])
            print("Files successfully installed")
    elif args.service == 'upstart':
        if _q('2 new files will be created: /etc/init/ftpvista.conf and /etc/init/ftpvista-oc.conf. Continue ?'):
            with open('/etc/init/ftpvista.conf', 'w') as ws:
                ws.write(fupstart.format(chdir=dirname, start='start', description='FTPVista'))
            with open('/etc/init/ftpvista-oc.conf', 'w') as ws:
                ws.write(fupstart.format(chdir=dirname, start='start-oc', description='FTPVista online checker'))
            print("Files successfully installed")
    return 0


def uninstall_logrotate(args):
    if os.path.isfile('/etc/logrotate.d/ftpvista'):
        if _q('/etc/logrotate.d/ftpvista will be deleted. Continue ?'):
            os.remove('/etc/logrotate.d/ftpvista')
            print("File successfully deleted")
    else:
        print('Nothing to delete for logrotate.')
    return 0


def install_logrotate(args):
    print('-- Logrotate installation --')
    if not _command_exists('logrotate'):
        print("logrotate doesn't seems to be intalled. Skipping.")
        return 1
    flogrotate = """{}/* {{
  rotate 0
  copytruncate
  size 10M
  missingok
  notifempty
}}
"""
    config = init_config(args)
    if _q('/etc/logrotate.d/ftpvista will be created. Continue ?'):
        with open('/etc/logrotate.d/ftpvista', 'w') as ws:
            ws.write(flogrotate.format(config.get('logs', 'folder')))
        print("File successfully installed")
    return 0


def uninstall_all(args):
    ret = 0
    ret |= uninstall_services(args)
    ret |= uninstall_logrotate(args)
    return ret


def install_all(args):
    ret = 0
    ret |= install_services(args)
    ret |= install_logrotate(args)
    return ret


def init():
    dirname = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="FTPVista 4.0 installer")
    parser.add_argument("-c", "--config", dest="config_file", metavar="FILE", default=os.path.join(dirname, 'ftpvista.conf'), help="Path to the config file")
    subparsers = parser.add_subparsers(dest='action')
    # install
    parser_install = subparsers.add_parser('install', help='Install FTPVista system elements')
    subparsers_install = parser_install.add_subparsers(dest='install_action')
    # install services
    parser_services = subparsers_install.add_parser('services', help='Generate and install services scripts for upstart or systemd')
    parser_services.set_defaults(func=install_services)
    parser_services.add_argument("service", nargs='?', choices=["upstart", "systemd"])
    # install logrotate
    parser_logrotate = subparsers_install.add_parser('logrotate', help='Generate and install logrotate specific configuration for FTPVista')
    parser_logrotate.set_defaults(func=install_logrotate)
    # install all
    parser_all = subparsers_install.add_parser('all', help='Install upstart or systemd scripts and logrotate script')
    parser_all.set_defaults(func=install_all)
    # uninstall
    parser_uninstall = subparsers.add_parser('uninstall', help='Uninstall FTPVista system elements')
    subparsers_uninstall = parser_uninstall.add_subparsers(dest='uninstall_action')
    # uninstall services
    parser_services = subparsers_uninstall.add_parser('services', help='Uninstall services scripts of upstart or systemd')
    parser_services.add_argument("service", nargs='?', choices=["upstart", "systemd"])
    parser_services.set_defaults(func=uninstall_services)
    # uninstall logrotate
    parser_logrotate = subparsers_uninstall.add_parser('logrotate', help='Uninstall logrotate specific configuration of FTPVista')
    parser_logrotate.set_defaults(func=uninstall_logrotate)
    # uninstall all
    parser_all = subparsers_uninstall.add_parser('all', help='Uninstall upstart or systemd scripts and logrotate script')
    parser_all.set_defaults(func=uninstall_all)

    args = parser.parse_args()

    if os.getuid() != 0:
        print("You must be root in order to run FTPVista installer. Exiting.")
        exit(1)

    return args.func(args)

if __name__ == '__main__':
    init()
