from django.db import models

# Create your models here.


class Userinfo(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=32)
    password = models.CharField(max_length=64)




