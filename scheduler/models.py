from django.db import models

# Create your models here.


class Course(models.Model):
    year = models.CharField(max_length=4)
    quarter = models.CharField(max_length=6)
    curriculum = models.CharField(max_length=12)
    number = models.CharField(max_length=3)
    section = models.CharField(max_length=2)


class Curriculum(models.Model):
    """ Maps curricula to campus code
    """
    curriculum_abbr = models.SlugField(max_length=20, unique=True)
    campus_code = models.SmallIntegerField(default=0)


class RecorderCache(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)


class RecorderCacheEntry(models.Model):
    cache = models.ForeignKey(RecorderCache,
                              related_name="+")
    recorder_id = models.CharField(max_length=36)
    recorder_external_id = models.CharField(max_length=32)
    name = models.CharField(max_length=128)
