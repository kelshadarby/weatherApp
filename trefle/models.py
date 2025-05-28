
from django.db import models

class Plants(models.Model):
    name = models.CharField(max_length=100)
    last_watered = models.DateTimeField()
    date_planted = models.DateTimeField()
    date_to_harvest = models.DateTimeField()
    plant_type = models.CharField(max_length=100)
    is_perennial = models.BooleanField()
    companion_plant_ids = models.CharField(max_length=100)
    date_fertilized = models.DateTimeField()
