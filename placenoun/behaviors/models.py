from django.db import models

# Create your models here.

class TimeStampable(models.Model):
  created_at = models.DateTimeField(auto_now_add = True, editable = False)
  updated_at = models.DateTimeField(auto_now = True, editable = False)

  class Meta:
    abstract = True
