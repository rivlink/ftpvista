# FTPVista

FTPVista est un moteur d'indexation et de recherche de serveurs FTP.

Il est actuellement en version 4.0 et codé en [Python 3](http://python.org/) (>=3.4).

## Installation
### Prérequis
Environnement Linux, avec droits d'administration.

### Dev
python3 manage.py migrate
python3 manage.py createsuperuser

### Préparation de l'environnement
Pour pouvoir faire fonctionner FTPVista en local sur votre machine, il faut:
  * Créer un utilisateur et un groupe _ftpvista_
```
groupadd ftpvista -g 4000
useradd ftpvista -m -u 4000 -g ftpvista
```
Le `-g 4000` pour la commande `groupadd` et le `-u 4000` pour la commande `useradd` affectent respectivement un gid et un uid à ftpvista. Il est possible de spécifier tout autre uid et gid non déjà utilisé par le système. Ces paramètres seront spécifiés dans le fichier de configuration.
  * Installer un environnement Python. Pour se faire il faut executer la commande suivante (sous [Debian](http://www.debian.org)):
```
aptitude install python3 python3-pip uwsgi uwsgi-plugin-python3 python3-pycurl
```
And if using apache
```
aptitude install libapache2-mod-proxy-uwsgi
a2enmod proxy
a2enmod proxy_uwsgi
```
Pour toute autre distrib, vous référez à sa documentation.

  * Il faut aussi installer les dépendances python requises (_scapy_ [v2.2 min.], _sqlalchemy_ et _django_ [v1.8 min.]):
```
aptitude install python3-sqlalchemy
pip3 install Whoosh scapy-python3 django pyftpdlib colorama
```


### Fichiers de paramétrage
Toutes les références à des fichiers dans cette catégorie seront faites relativement au dossier /home/ftpvista/ftpvista3/

#### ftpvista.conf
Il doit tout d'abord être créé à partir du fichier _ftpvista.default.conf_:
```
cp ftpvista.default.conf ftpvista.conf
```
C'est le fichier de configuration principal de FTPVista. Il est formaté comme un fichier .ini. Plus de détails dans les commentaires du fichier.

#### ftpvista.uwsgi
Fichier de configuration permettant à _uwsgi_ de lancer le serveur web de FTPVista.

### Fonctionnement
Dans cette partie sera abordé le fonctionnement d'FTPVista.

#### Moteur d'indexation et détecteur de serveurs en ligne
Tout ce qui concerne le moteur d'indexation et le détecteur de serveurs en ligne se situe dans le dossier _ftpvista_.

  * **ftpvista.py** : Fichier principal d'FTPVista, c'est lui qui est éxécuté. Il contient donc le _main_ dans lequel se situe en premier lieu la gestion des options de la ligne de commande:
```
usage: ftpvista.py [-h] [-c FILE]
                   {install-services,start,start-oc,clean,delete} ...

FTPVista 4.0

positional arguments:
  {install-services,start,start-oc,clean,delete}
    install-services    Generate and install services scripts for upstart or
                        systemd
    start               Start FTPVista
    start-oc            Start online checker
    clean               Empty the index, or the database, or everything !
    delete              Manually delete a server from the index

optional arguments:
  -h, --help            show this help message and exit
  -c FILE, --config FILE
                        Path to the config file
```
Note: **ftpvista.py** doit toujours être lancé en **root** (via _sudo_ par exemple).

### Mise en place de logrotate
FTPVista peut potentiellement écrire beaucoup de logs dans le fichier indexer.log. Il est donc nécessaire de configurer un logrotate pour que ce fichier ne dépasse pas les 10Mo.

Pour ce faire, il faut créer un fichier `/etc/logrotate.d/ftpvista` avec le contenu suivant :

```
/var/log/ftpvista/* {
  rotate 0
  copytruncate
  size 10M
  missingok
  notifempty
}
```
