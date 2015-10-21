from django.db import models
from django.core.exceptions import ObjectDoesNotExist


class Correspondence(models.Model):
    ip = models.GenericIPAddressField(protocol='IPv4')
    name = models.CharField(max_length=20)

    @staticmethod
    def getbyip(ip):
        try:
            return Correspondence.objects.get(ip=ip)
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def getbyname(name):
        try:
            return Correspondence.objects.get(name=name)
        except ObjectDoesNotExist:
            return None

    def __str__(self):
        return "{} ({})".format(self.name, self.ip)
