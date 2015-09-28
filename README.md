# FTPVista

FTPVista est un moteur d'indexation et de recherche de serveur FTP.

Il est actuellement en version 3.0 et codé en [Python 2](http:_python.org/).

## Ce qu'il faut savoir
### Prérequis
Environnement Linux, avec droits d'administration.

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
aptitude install python3 python3-pip
```
Pour toute autre distrib, vous référez à sa documentation.
  * FTPVista nécessite aussi l'installation d'_apache_:
```
aptitude install apache2 libapache2-mod-python libapache2-mod-wsgi
```
  * Il faut aussi installer les dépendances python requises (_scapy_ [v2.2 min.], _sqlalchemy_ et _django_ [v1.8 min.]):
```
# aptitude install python-scapy python-sqlalchemy python-django python-argparse python-daemon python-pycurl python-mysqldb
aptitude install python3-sqlalchemy
pip3 install Whoosh scapy-python3 django
```
  * Et configurer _apache_. Pour ce faire il suffit de rajouter les lignes suivantes dans le fichier /etc/apache2/sites-available/default, juste avant la ligne </VirtualHost> (il est aussi possible de créer un autre fichier dans le dossier sites-available et de le linker dans sites-enabled):
```apache
WSGIScriptAlias /ftpvista3 /home/ftpvista/ftpvista3/apache/django.wsgi

<Directory /home/ftpvista/ftpvista3/apache>
        Require all granted
</Directory>
```
Puis redémarrer Apache
```
sudo service apache restart
```

### Fichiers de paramétrage
Toutes les références à des fichiers dans cette catégorie seront faites relativement au dossier /home/ftpvista/ftpvista3/

#### ftpvista.conf
C'est le fichier de configuration principal de FTPVista. Il est formaté comme un fichier .ini. Chaque catégorie énoncée ci-dessous est une catégorie dans le fichier de configuration représentée de cette manière :
```
[categorie]
```

##### logs
Contient les informations sur les logs
  * main (default: /var/log/ftpvista/indexer.log) : Chemin vers le fichier de log du moteur d'indexation
  * online_checker (default: /var/log/ftpvista/checker.log) : Chemin vers le fichier de log du vérificateur de serveurs en ligne

Ici, le dossier /var/log/ftpvista doit exister et appartenir à ftpvista:www-data avec les droits 775.
```
  sudo mkdir -p /var/log/ftpvista
  sudo chown ftpvista:www-data /var/log/ftpvista
```

##### db
Contient les informations concernant la base de données
  * uri (default: sqlite://home/ftpvista/ftpvista.db) : URI vers le fichier de base de données SQLITE
  
##### index
Contient les informations concernant l'index whoosh
  * uri (default: /home/ftpvista/ftpvista_idx) : Chemin vers le dossier qui contiendra les fichiers de l'index Whoosh.

##### indexer

Contient les informations sur le moteur d'indexation
  * pid (default: /var/run/ftpvista.pid) : Chemin vers le fichier PID (utilisé par le mode daemon)
  * working_directory (default: /home/ftpvista/ftpvista3) : Chemin d’exécution utilisé par le mode daemon
  * uid (default: valeur spécifiée plus haut par l'option _-u_ de la commande _useradd_) : UID du moteur d'indexation (inutilisé pour l'instant)
  * gid (default: valeur spécifiée plus haut par l'option _-g_ de la commande _groupadd_) : GID du moteur d'indexation (inutilisé pour l'instant)
  * blacklist (default: _vide_) : Liste d'IP (séparées par une virgule) à ne pas scanner
  * subnet (default: 10.20.0.0/21) : Sous réseau sur lequel se situent les potentiels serveurs FTP
  * scanner_interval (default: 1800) : Interval en secondes au bout duquel on rescanne le subnet pour de nouveaux serveurs FTP
  * valid_ip_pattern (default: `^10\.20\.[01234567]\.\d{1,3}$`) : Schema d'expression régulière utilisé pour tester la validité d'une IP
  * min_update_interval (default: 2) : Interval en heures au bout duquel une indexation pour un même serveur est relancée
  * max_depth (default: 50) : Profondeur maximale à laquelle le moteur ira chercher des fichiers (permet d'éviter la récursivité infinie)

##### online_checker

  * update_interval (default: 300) : Interval en secondes au bout duquel on teste si un serveur est online
  * purge_interval (default: 30) : Interval en jours au bout duquel un serveur est supprimé de l'index si son état est resté hors connexion pendant tout ce temps
  * pid (default: /var/run/ftpvista_online_checker.pid) : Chemin vers le fichier PID du vérificateur de serveurs en ligne
  * uid (default: valeur spécifiée plus haut pas l'option _-u_ de la commande _useradd_) : UID du moteur d'indexation (inutilisé pour l'instant)
  * gid (default: valeur spécifiée plus haut pas l'option _-g_ de la commande _groupadd_) : GID du moteur d'indexation (inutilisé pour l'instant)

#### correspondences.ftp
Fichier ASCII contenant par ligne une association IP Surnom (séparés par une tabulation).

#### ftpvista.sh
Fichier à placer dans /etc/init.d/ pour lancer ftpvista en daemon. Ce fichier contient les parametres suivants :
  * DAEMON (default: /home/ftpvista/ftpvista3/ftpvista/ftpvista.py) : Chemin vers le fichier d'FTPVista à éxécuter
  * PID (default: /var/run/ftpvista.pid) : Chemin vers le fichier PID du moteur d'indexation. **Doit être le même que celui spécifié dans le fichier _ftpvista.conf_, section _indexer_**
  * PID2 (default: /var/run/ftpvista_online_checker.pid) : Chemin vers le fichier PID du vérificateur de serveurs en ligne. **Doit être le même que celui spécifié dans le fichier _ftpvista.conf_, section _online_checker_**
  * DESC (default: FTPVista) : Description minimale du daemon

#### magnesite/settings.py
Fichier de configuration concernant l'interface Web, plus d'informations sur le site de [Django](http:_docs.djangoproject.com/en/dev/ref/settings/).
Les variables importantes sont les suivantes:
  * WHOOSH_IDX (default: '/home/ftpvista/ftpvista_idx') : Chemin vers le dossier contenant l'index Whoosh. **Doit être le même que pour le fichier _ftpvista.conf_**
  * PERSIST_DB (default: 'sqlite:__home/ftpvista/ftpvista.db') : Chemin vers le fichier SQLITE. **Doit être le même que pour le fichier _ftpvista.conf_**
  * ROOT_URLCONF (default: 'magnesite.urls') : variable python contenant les informations sur les URL
  * TEMPLATE_DIRS (default: ("/home/ftpvista/ftpvista3/magnesite/templates")) : Liste des dossiers contenant les templates
  * LOG_PATH (default: '/var/log/ftpvista/search.log') : Chemin vers le fichier de log pour la recherche. **Le fichier doit pouvoir être écrit pour l'utilisateur apache (communément _www-data:www-data_)**

#### magnesite/urls.py
Fichier de configuration contenant la variable _urls_ (cf. variable ROOT_URLCONF du fichier _magnesite/settings.py_). Plus d'informations sur le site de [Django](http://docs.djangoproject.com/en/dev/topics/http/urls/).

### Fonctionnement
Dans cette partie sera abordé le fonctionnement d'FTPVista. Pour un fonctionnement détaillé du programme, cf. les commentaires des sources.

#### Moteur d'indexation et détecteur de serveurs en ligne
Tout ce qui concerne le moteur d'indexation et le détecteur de serveurs en ligne se situe dans le dossier _ftpvista_.

  * **ftpvista.py** : Fichier principal d'FTPVista, c'est lui qui est éxécuté. Il contient donc le _main_ dans lequel se situe en premier lieu la gestion des options de la ligne de commande:
```
usage: ftpvista.py [-h] [-v] [-c FILE] [-d] {start,start-oc,clean,delete} ...

positional arguments:
  {start,start-oc,clean,delete}
    start               Start FTPVista
    start-oc            Start Online checker
    clean               Empty the index, or the database, or everything !
    delete              Manually delete a server from the index

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -c FILE, --config FILE
                        Path to the config file
  -d, --daemon          Run FTPVista as a Daemon
```
  * Pour les autres fichiers, cf. source.

### Mise en place de logrotate
FTPVista peut potentiellement écrire beaucoup de logs dans le fichier indexer.log. Il est donc nécessaire de configurer un logrotate pour que ce fichier ne dépasse pas les 100Mo.

Pour ce faire, il faut créer un fichier `/etc/logrotate.d/ftpvista` avec le contenu suivant :

```
/var/log/ftpvista/* {
  rotate 0
  copytruncate
  size 100M
  missingok
  notifempty
}
```