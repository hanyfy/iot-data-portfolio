from django.db import models

# Create your models here.


class ApiZone(models.Model):
    id_api = models.fields.IntegerField() # primary key
    name = models.fields.CharField(max_length=100)
    base_url = models.fields.TextField()


class AccessApi(models.Model):
    id_access = models.fields.IntegerField() # primary key
    id_api = models.fields.IntegerField() # Foreign  Key
    login = models.fields.CharField(max_length=100)
    password =  models.fields.CharField(max_length=100)


class HeaderApi(models.Model):
    id_header = models.fields.IntegerField() #primary key
    id_api = models.fields.IntegerField() # Foreign Key
    key = models.fields.CharField(max_length=200)
    value = models.fields.CharField(max_length=200)

