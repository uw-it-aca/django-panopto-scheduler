# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.db import models


class Curriculum(models.Model):
    """ Maps curricula to campus code
    """
    curriculum_abbr = models.SlugField(max_length=20, unique=True)
    campus_code = models.SmallIntegerField(default=0)


class RecorderCache(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)


class RecorderCacheEntry(models.Model):
    cache = models.ForeignKey(RecorderCache,
                              on_delete=models.PROTECT,
                              related_name="+")
    recorder_id = models.CharField(max_length=36)
    recorder_external_id = models.CharField(max_length=32)
    name = models.CharField(max_length=128)
