#!/usr/bin/env python3

import os
import re
import grp
import pwd
import sys
import glob
import shutil
import random
import argparse
import readline
import ipaddress
import subprocess
import configparser
from colorama import init as colorama_init, Fore
from django.core.management import execute_from_command_line


def default(func):
    def func_wrapper(obj, userinput):
        if userinput == '' and hasattr(obj, 'default') and obj.default is not None:
            userinput = obj.default
        return func(obj, userinput)
    return func_wrapper


class Question:
    """
    Abstract class
    """

    def before_raw_input(self):
        pass

    def after_raw_input(self):
        pass

    def question(self):
        raise('This method must be overhidden')

    @default
    def answer(self, answer):
        if hasattr(self, 'callback') and self.callback is not None:
            return self.callback(answer)
        return answer

    def prompt(self, prompt):
        if hasattr(self, 'default') and self.default is not None:
            return '[default: {default}] {prompt}'.format(prompt=prompt, default=self.default)
        return prompt

    def check(self, userinput):
        raise('This method must be overhidden')


class Text(Question):

    def __init__(self, text, default=None, callback=None):
        self.text = text
        self.default = default
        self.callback = callback
        self.newline = True

    def question(self):
        return self.text

    def check(self, userinput):
        return True


class Int(Text):

    def __init__(self, text, default=None, callback=lambda a: int(a)):
        self.text = text
        self.default = default
        self.callback = callback
        self.newline = True

    @default
    def check(self, userinput):
        try:
            int(userinput)
        except ValueError:
            return False
        return True


class Subnet(Text):

    @default
    def check(self, userinput):
        try:
            ipaddress.ip_network(userinput)
            return True
        except ValueError:
            return False


class Choices(Question):
    """
    Multiple choices oriented questions class
    """

    def __init__(self, text, choices, default=None, callback=None):
        self.text = text
        self.default = default
        self.callback = callback
        self.whitelist = choices

    def question(self):
        return '{} ({})'.format(self.text, "/".join(self.whitelist))

    @default
    def check(self, userinput):
        if userinput in self.whitelist:
            return True
        return False


class YesNo(Choices):

    def __init__(self, text, callback=lambda a: a.lower() == 'y'):
        self.text = text
        self.callback = callback
        self.whitelist = ['y', 'n']

    def question(self):
        return (self.text + ' [y/n] ')


class Path(Text):

    def _complete(self, text, state):
        return (glob.glob(text+'*')+[None])[state]

    def before_raw_input(self):
        readline.set_completer_delims(' \t\n;')
        readline.parse_and_bind('tab: complete')
        readline.set_completer(self._complete)

    def after_raw_input(self):
        readline.set_completer()


class Ask:

    asking = False

    def __init__(self, prompt='-> '):
        self.ps = prompt

    @staticmethod
    def _print(s, newline=True):
        """
        Prints something only if a prompt is not displayed
        """
        if not Ask.asking:
            sys.stdout.write('\r'+s)
            if newline:
                sys.stdout.write('\n')
            sys.stdout.flush()

    def ask(self, q):
        """
        Prints the question and input for user answer
        """
        print(q.question())
        while True:
            Ask.asking = True
            q.before_raw_input()
            answer = input(q.prompt(self.ps))
            q.after_raw_input()
            if q.check(answer):
                a = q.answer(answer)
                if isinstance(a, Question):
                    Ask.asking = False
                    return self.ask(a)
                else:
                    Ask.asking = False
                    return a


def w(text):
    return Fore.YELLOW + text + Fore.RESET


def e(text):
    return Fore.RED + text + Fore.RESET


def s(text):
    return Fore.GREEN + text + Fore.RESET


def i(text):
    return Fore.BLUE + text + Fore.RESET


def _user_exists(name, uid):
    try:
        pwd.getpwnam(name)
        return True
    except KeyError:
        pass
    try:
        pwd.getpwuid(uid)
        return True
    except KeyError:
        pass
    return False


def _user_coherence(name, uid):
    try:
        return pwd.getpwnam(name).pw_uid == uid
    except KeyError:
        return pwd.getpwuid(uid).pw_name == name


def _group_exists(name, gid):
    try:
        grp.getgrnam(name)
        return True
    except KeyError:
        pass
    try:
        grp.getgrgid(gid)
        return True
    except KeyError:
        pass
    return False


def _group_coherence(name, gid):
    try:
        return grp.getgrnam(name).gr_gid == gid
    except KeyError:
        return grp.getgrgid(gid).gr_name == name


def _stat_proc1exe():
    regex = re.compile("^.* -> .(.*).$")
    out = subprocess.check_output(["stat", "--format", "%N", "/proc/1/exe"]).decode().strip()
    matches = regex.match(out)
    return matches.group(1)


def _command_exists(command):
    with open(os.devnull, "w") as f:
        return subprocess.call(["which", command], stdout=f) == 0


def uninstall_services(args):
    print(i('Services'))
    a = Ask()
    if not hasattr(args, 'service') or args.service == 'upstart':
        if os.path.isfile('/etc/init/ftpvista.conf') or os.path.isfile('/etc/init/ftpvista-oc.conf') or os.path.isfile('/etc/init/ftpvista-uwsgi.conf'):
            if a.ask(YesNo('Delete /etc/init/ftpvista.conf, /etc/init/ftpvista-oc.conf and /etc/init/ftpvista-uwsgi.conf ?')):
                if os.path.exists('/etc/init/ftpvista.conf'):
                    os.remove('/etc/init/ftpvista.conf')
                if os.path.exists('/etc/init/ftpvista-oc.conf'):
                    os.remove('/etc/init/ftpvista-oc.conf')
                if os.path.exists('/etc/init/ftpvista-uwsgi.conf'):
                    os.remove('/etc/init/ftpvista-uwsgi.conf')
                print(s("Files successfully deleted."))
        else:
            print('Nothing to delete for service upstart.')
    elif not hasattr(args, 'service') or args.service == 'systemd':
        if os.path.isfile('/etc/systemd/system/ftpvista.service') or os.path.isfile('/etc/systemd/system/ftpvista-oc.service'):
            if a.ask(YesNo('Delete /etc/systemd/system/ftpvista.service and /etc/systemd/system/ftpvista-oc.service ?')):
                print("Disabling services via systemctl")
                subprocess.call(["systemctl", "disable", "ftpvista"])
                subprocess.call(["systemctl", "disable", "ftpvista-oc"])
                subprocess.call(["systemctl", "disable", "ftpvista-uwsgi"])
                if os.path.exists('/etc/systemd/system/ftpvista.service'):
                    os.remove('/etc/systemd/system/ftpvista.service')
                if os.path.exists('/etc/systemd/system/ftpvista-oc.service'):
                    os.remove('/etc/systemd/system/ftpvista-oc.service')
                if os.path.exists('/etc/systemd/system/ftpvista-uwsgi.service'):
                    os.remove('/etc/systemd/system/ftpvista-uwsgi.service')
                print(s("Files successfully deleted."))
        else:
            print('Nothing to delete for service systemd.')
    return 0


def install_uwsgi_services(args):
    if args.service != 'skip':
        fupstart = """description "FTPVista uwsgi instance"
author "joel.charles91@gmail.com"

start on runlevel [2345]
stop on runlevel [06]
console log
chdir {chdir}
env LANG="en_US.UTF-8"
setuid {uid}
setgid {gid}

respawn

exec uwsgi --ini {root}/festival.uwsgi
"""
        fsystemd = """[Unit]
Description=FTPVista uwsgi instance
After=network.target

[Service]
User={uid}
Group={gid}
ExecStart=/usr/bin/uwsgi --ini {root}/festival.uwsgi
WorkingDirectory={chdir}
Restart=always
KillSignal=SIGQUIT
Type=notify

[Install]
WantedBy=multi-user.target
"""
        dirname = os.path.dirname(os.path.realpath(__file__))
        a = Ask()
        if args.service == 'systemd':
            if a.ask(YesNo('Create /etc/systemd/system/ftpvista-uwsgi.service ?')):
                with open('/etc/systemd/system/ftpvista-uwsgi.service', 'w') as ws:
                    ws.write(fsystemd.format(chdir=dirname, root=args.root, uid=args.uid, gid=args.gid))
                print("Enabling uwsgi service via systemctl.")
                subprocess.call(["systemctl", "enable", "ftpvista-uwsgi"])
                print(s("File successfully installed."))
        elif args.service == 'upstart':
            if a.ask(YesNo('Create /etc/init/ftpvista-uwsgi.conf ?')):
                with open('/etc/init/ftpvista-uwsgi.conf', 'w') as ws:
                    ws.write(fupstart.format(chdir=dirname, root=args.root, uid=args.uid, gid=args.gid))
                print(s("File successfully installed."))


def install_services(args):
    print(i('Services'))
    a = Ask()
    if '/systemd' in _stat_proc1exe():
        args.service = 'systemd'
    else:
        args.service = 'upstart'
    args.service = a.ask(Choices('Choose service scripts to install', ['systemd', 'upstart', 'skip'], default=args.service))

    if args.service != 'skip':
        fupstart = """description "{description}"
author "joel.charles91@gmail.com"

start on runlevel [2345]
stop on runlevel [!2345]

chdir {chdir}
exec {chdir}/ftpvista.py --config "{config_path}" {start}
"""
        fsystemd = """[Unit]
Description={description}

After=network.target

[Service]
WorkingDirectory={chdir}
ExecStart={chdir}/ftpvista.py --config "{config_path}" {start}

[Install]
WantedBy=multi-user.target
"""
        dirname = os.path.dirname(os.path.realpath(__file__))
        if args.service == 'systemd':
            if a.ask(YesNo('2 new files will be created: /etc/systemd/system/ftpvista.service and /etc/systemd/system/ftpvista-oc.service. Continue ?')):
                with open('/etc/systemd/system/ftpvista.service', 'w') as ws:
                    ws.write(fsystemd.format(chdir=dirname, config_path=args.config_path, start='start', description='FTPVista'))
                with open('/etc/init/ftpvista-oc.conf', 'w') as ws:
                    ws.write(fsystemd.format(chdir=dirname, config_path=args.config_path, start='start-oc', description='FTPVista online checker'))
                print("Enabling services via systemctl.")
                subprocess.call(["systemctl", "enable", "ftpvista"])
                subprocess.call(["systemctl", "enable", "ftpvista-oc"])
                print(s("Files successfully installed."))
        elif args.service == 'upstart':
            if a.ask(YesNo('2 new files will be created: /etc/init/ftpvista.conf and /etc/init/ftpvista-oc.conf. Continue ?')):
                with open('/etc/init/ftpvista.conf', 'w') as ws:
                    ws.write(fupstart.format(chdir=dirname, config_path=args.config_path, start='start', description='FTPVista'))
                with open('/etc/init/ftpvista-oc.conf', 'w') as ws:
                    ws.write(fupstart.format(chdir=dirname, config_path=args.config_path, start='start-oc', description='FTPVista online checker'))
                print(s("Files successfully installed."))
    return 0


def uninstall_logrotate(args):
    print(i('Logrotate'))
    a = Ask()
    if os.path.isfile('/etc/logrotate.d/ftpvista'):
        if a.ask(YesNo('/etc/logrotate.d/ftpvista will be deleted. Continue ?')):
            os.remove('/etc/logrotate.d/ftpvista')
            print(s("File successfully deleted."))
    else:
        print('Nothing to delete for logrotate.')
    return 0


def install_logrotate(args):
    print(i('Logrotate'))
    a = Ask()
    if not _command_exists('logrotate'):
        print(w("logrotate doesn't seems to be intalled. Skipping."))
        return 1
    flogrotate = """{}/logs/* {{
  rotate 0
  copytruncate
  size 10M
  missingok
  notifempty
}}
"""
    if a.ask(YesNo('/etc/logrotate.d/ftpvista will be created. Continue ?')):
        with open('/etc/logrotate.d/ftpvista', 'w') as ws:
            ws.write(flogrotate.format(args.root))
        print(s("File successfully installed."))
    return 0


def install_user(args):
    print(i('Create/Use user'))
    a = Ask()
    with open(os.devnull, "w") as f:
        # Group
        args.gname = a.ask(Text('New unix group name', default='ftpvista'))
        args.gid = a.ask(Int('New unix group ID', default='4000'))
        if _group_exists(args.gname, args.gid):
            if _group_coherence(args.gname, args.gid):
                print(w("Group {} or gid({}) already exists. Skipping.".format(args.gname, args.gid)))
            else:
                print(e("Group {} or gid({}) do not match in Unix group database. Aborting.".format(args.gname, args.gid)))
                exit(2)
        else:
            subprocess.call(["groupadd", args.gname, "-g", str(args.gid)], stdout=f)
            print(s("Group {} gid({}) successfully added.".format(args.gname, args.gid)))
        # User
        args.uname = a.ask(Text('New unix user name', default='ftpvista'))
        args.uid = a.ask(Int('New unix user ID', default='4000'))
        if _user_exists(args.uname, args.uid):
            if _user_coherence(args.uname, args.uid):
                print(w("User {} or uid({}) already exists. Skipping.".format(args.uname, args.uid)))
            else:
                print(e("User {} or uid({}) do not match in Unix user database. Aborting.".format(args.uname, args.uid)))
                exit(3)
        else:
            subprocess.call(["useradd", args.uname, "-m", "-u", str(args.uid), "-g", args.gname], stdout=f)
            print(s("User {} uid({}) successfully added.".format(args.uname, args.uid)))
    return 0


def uninstall_user(args, config):
    print(i('Delete user'))
    a = Ask()
    try:
        gname = grp.getgrgid(config.getint('indexer', 'gid')).gr_name
    except KeyError:
        gname = None
    try:
        uname = pwd.getpwuid(config.getint('indexer', 'uid')).pw_name
    except KeyError:
        uname = None
    if uname is not None:
        with open(os.devnull, "w") as f:
            if a.ask(YesNo('Are you sure you want to remove user {} and group {} ?'.format(uname, gname))):
                subprocess.call(["deluser", "--remove-home", "--quiet", uname], stdout=f)
                subprocess.call(["delgroup", "--remove-home", "--quiet", gname], stdout=f)
                print(s('User successfully deleted.'))
            else:
                print('Skipping user deletion.')
    else:
        print(w('User uid({}) does not exists. Skipping/'.format(config.get('indexer', 'uid'))))
    return 0


def install_configuration(args):
    print(i('Configuration'))
    a = Ask()
    dirname = os.path.dirname(os.path.abspath(__file__))
    config = configparser.SafeConfigParser()
    config.read(os.path.join(dirname, 'ftpvista.default.conf'))
    # Ask for root directory
    if hasattr(args, 'uname'):
        default_root = os.path.join('/home', args.uname, 'ftpvista')
    else:
        default_root = None
    path_valid = False
    while not path_valid:
        chosen_root = a.ask(Path('FTPVista root folder', default=default_root))
        if os.path.exists(chosen_root):
            if os.path.isdir(chosen_root):
                if len(os.listdir(chosen_root)) > 0:
                    print(w('The specified directory already exists and is not empty. Please choose another directory.'))
                else:
                    path_valid = True
            else:
                print(w('The specified path already exists and is not a directory.'))
        else:
            path_valid = True
    # Subnet
    args.subnet = a.ask(Subnet('Subnet to scan for FTP servers', default=config.get('indexer', 'subnet')))
    # Create root directory
    if os.path.exists(chosen_root):
        os.rmdir(chosen_root)
    logs_dir = os.path.join(chosen_root, 'logs')
    os.makedirs(logs_dir, mode=0o775)
    os.chown(chosen_root, args.uid, args.gid)
    os.chown(logs_dir, args.uid, args.gid)
    print(s('Directory {} created'.format(chosen_root)))
    # Customize final configuration file
    config.set('logs', 'folder', os.path.join(chosen_root, 'logs'))
    config.set('django', 'secret_key', ''.join([random.SystemRandom().choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$^&*(-_=+)') for i in range(50)]))
    config.set('db', 'uri', 'sqlite:///' + os.path.join(chosen_root, 'ftpvista.db'))
    config.set('index', 'uri', os.path.join(chosen_root, 'ftpvista_idx'))
    config.set('indexer', 'uid', str(args.uid))
    config.set('indexer', 'gid', str(args.gid))
    config.set('indexer', 'subnet', args.subnet)
    config.set('online_checker', 'uid', str(args.uid))
    config.set('online_checker', 'gid', str(args.gid))
    # Generate final configuration file
    config_path = os.path.join(chosen_root, 'ftpvista.conf')
    with os.fdopen(os.open(config_path, os.O_WRONLY | os.O_CREAT, mode=0o660), 'w') as cf:
        config.write(cf, space_around_delimiters=False)
    os.chown(config_path, args.uid, args.gid)
    args.root = chosen_root
    args.config_path = config_path
    print(s('Config written to ' + config_path))


def uninstall_configuration(args):
    print(i('Home directory'))
    a = Ask()
    if a.ask(YesNo('Delete {} directory ?'.format(args.home))):
        shutil.rmtree(args.home)
        print(s(args.home + ' successfully deleted.'))
    else:
        print(args.home, 'not deleted.')


def install_uwsgi(args):
    fuwsgi = """[uwsgi]
chdir={chdir}
socket=127.0.0.1:15600
module=ftpvistasite.wsgi:application
master=True
plugins=python3
static-map=/static=%d/ftpvistasite/static
config_path={config_path}"""
    dirname = os.path.dirname(os.path.abspath(__file__))
    uwsgi_path = os.path.join(args.root, 'ftpvista.uwsgi')
    with open(uwsgi_path, 'w') as wf:
        wf.write(fuwsgi.format(chdir=dirname, config_path=args.config_path))
    print(s('{} successfully created'.format(uwsgi_path)))


def configure_apache():
    print(w(os.linesep+'Next step must be done manually'))
    print("""Add this snippet into your apache VirtualHost:
ProxyPass /ftpvista uwsgi://127.0.0.1:15600/""")


def init_django(args):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ftpvistasite.settings")
    os.environ.setdefault("CONFIG_PATH", args.config_path)
    print(i('Django database'))
    execute_from_command_line(['migrate', 'migrate'])
    print(i('Django admin user'))
    execute_from_command_line(['migrate', 'createsuperuser'])
    os.chown(os.path.join(args.root, 'ftpvista.db'), args.uid, args.gid)


def check_home(args):
    config_path = os.path.join(args.home, 'ftpvista.conf')
    if os.path.exists(config_path):
        config = configparser.SafeConfigParser()
        config.read(config_path)
        return config
    return None


def main(args):
    if args.action == 'install':
        if args.user or args.all:
            install_user(args)
        if args.configuration or args.all:
            install_configuration(args)
        if args.services or args.all:
            if args.home is not None:
                args.config_path = os.path.join(args.home, 'ftpvista.conf')
            install_services(args)
            if args.webserver or args.all:
                install_uwsgi_services(args)
        if args.logrotate or args.all:
            if args.home is not None:
                args.root = args.home
            install_logrotate(args)
        if args.webserver or args.all:
            if args.home is not None:
                args.root = args.home
                args.config_path = os.path.join(args.home, 'ftpvista.conf')
            init_django(args)
            install_uwsgi(args)
            configure_apache()
        return 0
    elif args.action == 'uninstall':
        if args.user or args.all:
            config = check_home(args)
            if config is None:
                print(e('No config file found in {}. Aborting.'.format(args.home)))
                exit(6)
        if args.configuration or args.all:
            uninstall_configuration(args)
        if args.user or args.all:
            uninstall_user(args, config)
        if args.services or args.all:
            uninstall_services(args)
        if args.logrotate or args.all:
            uninstall_logrotate(args)
        return 0
    return 1


def init():
    colorama_init()
    parser = argparse.ArgumentParser(description="FTPVista 4.0 installer")
    parser.add_argument('--user', action='store_true', help='Create/delete unix user of FTPVista', default=False)
    parser.add_argument('--configuration', action='store_true', help='(Un)install configuration file and FTPVista root directory', default=False)
    parser.add_argument('--services', action='store_true', help='(Un)install upstart or systemd services scripts', default=False)
    parser.add_argument('--logrotate', action='store_true', help='(Un)install logrotate configuration file', default=False)
    parser.add_argument('--webserver', action='store_true', help='(Un)install uwsgi script and create apache Virtual Host', default=False)
    parser.add_argument('--all', action='store_true', help='(Un)install everything')
    subparsers = parser.add_subparsers(dest='action')
    parser_install = subparsers.add_parser('install', help='Install FTPVista system elements')
    parser_install.add_argument('home', help='FTPVista home path', nargs='?', default=None)
    parser_uninstall = subparsers.add_parser('uninstall', help='Uninstall FTPVista system elements')
    parser_uninstall.add_argument('home', help='FTPVista home path')
    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        exit(1)

    if not args.user and not args.configuration and not args.services and not args.logrotate and not args.webserver:
        args.all = True

    if args.configuration and not args.all:
        args.user = True

    if os.getuid() != 0:
        print("You must be root in order to run FTPVista installer. Exiting.")
        exit(1)

    if args.action == 'install' and not args.all and args.home is None and (args.services or args.logrotate or args.webserver):
        print(w('home parameter is mandatory here. (install.py --abc install <home>)'))
        exit(1)

    return main(args)

if __name__ == '__main__':
    exit(init())
