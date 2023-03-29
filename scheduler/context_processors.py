# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
import os


def has_less_compiled(request):
    """ See if django-compressor is being used to precompile less
    """
    key = getattr(settings, "COMPRESS_PRECOMPILERS", None)
    return {"has_less_compiled": key != ()}


def debug_mode(request):
    return {"debug_mode": settings.DEBUG}


def event_schedule_buffers(request):
    return {'event_start_time_buffer': getattr(
        settings, 'EVENT_START_TIME_BUFFER', 0)}


def localdev_mode(request):
    return {'localdev_mode': (os.environ.get('ENV', None) == 'localdev')}
