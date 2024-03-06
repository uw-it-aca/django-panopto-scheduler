# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.shortcuts import render
from uw_sws.term import get_current_term
from restclients_core.exceptions import DataFailureException
from scheduler.exceptions import StudentWebServiceUnavailable
from uw_saml.decorators import group_required
from uw_saml.utils import is_member_of_group
import logging
import time


logger = logging.getLogger(__name__)


def build_view_context(request):
    try:
        term = get_current_term()
    except DataFailureException as ex:
        logger.info(ex)
        raise StudentWebServiceUnavailable()

    return {
        'term_year': term.year,
        'term_quarter': term.quarter,
        'todays_date': time.strftime("%Y-%m-%d"),
        'canvas_host': getattr(settings, "RESTCLIENTS_CANVAS_HOST", ""),
        'panopto_server': getattr(settings, "PANOPTO_SERVER", ""),
    }


@group_required(settings.PANOPTO_ADMIN_GROUP)
def home(request):
    context = build_view_context(request)
    return render(request, 'scheduler/home.html', context)


@group_required(settings.PANOPTO_ADMIN_GROUP)
def courses(request):
    context = build_view_context(request)
    return render(request, 'scheduler/courses.html', context)


@group_required(settings.PANOPTO_ADMIN_GROUP)
def events(request):
    context = build_view_context(request)
    return render(request, 'scheduler/events.html', context)


@group_required(settings.PANOPTO_ADMIN_GROUP)
def recorders(request):
    context = build_view_context(request)
    return render(request, 'scheduler/recorders.html', context)


def can_view_restclients_data(request, service=None, url=None):
    return is_member_of_group(request, settings.PANOPTO_ADMIN_GROUP)
