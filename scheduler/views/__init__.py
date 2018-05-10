from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from uw_sws.term import get_current_term
from restclients_core.exceptions import DataFailureException
from scheduler.exceptions import StudentWebServiceUnavailable
from userservice.user import UserService
from authz_group import Group
import logging
import time


logger = logging.getLogger(__name__)


def is_user_authorized():
    return Group().is_member_of_group(
        UserService().get_user(), settings.PANOPTO_ADMIN_GROUP)


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


@login_required
def home(request):
    if not is_user_authorized():
        return HttpResponseRedirect("/")

    context = build_view_context(request)
    return render(request, 'scheduler/home.html', context)


@login_required
def courses(request):
    if not is_user_authorized():
        return HttpResponseRedirect("/")

    context = build_view_context(request)
    return render(request, 'scheduler/courses.html', context)


@login_required
def events(request):
    if not is_user_authorized():
        return HttpResponseRedirect("/")

    context = build_view_context(request)
    return render(request, 'scheduler/events.html', context)


@login_required
def recorders(request):
    if not is_user_authorized():
        return HttpResponseRedirect("/")

    context = build_view_context(request)
    return render(request, 'scheduler/recorders.html', context)
