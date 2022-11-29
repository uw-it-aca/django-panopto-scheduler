# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.db import models
from scheduler.user import User


class Event(models.Model):
    is_crosslisted = models.BooleanField(null=True)


class Reservation(models.Model):
    event_name = models.CharField(max_length=64)
    profile_name = models.CharField(max_length=32)
    contact_name = models.CharField(max_length=64)
    contact_email = models.CharField(max_length=128)
    space_id = models.CharField(max_length=64, null=True)
    space_name = models.CharField(max_length=128, null=True)
    space_formal_name = models.CharField(max_length=128, null=True)
    is_instruction = models.BooleanField(null=True)
    is_course = models.BooleanField(null=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()

    def contact_info(self):
        return {
            'name': self.contact_name,
            'loginid': User().validate_login_id(self.contact_email),
            'email': self.contact_email
        }


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
