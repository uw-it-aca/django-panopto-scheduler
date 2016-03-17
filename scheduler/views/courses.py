from django.conf import settings
from django.template import RequestContext, loader
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from restclients.sws.term import get_current_term
from restclients.exceptions import DataFailureException
from userservice.user import UserService
from authz_group import Group
from scheduler.exceptions import StudentWebServiceUnavailable
import json
import time
import logging


logger = logging.getLogger(__name__)


@login_required
def courses(request, template='scheduler/courses.html'):
    user = UserService().get_original_user()
    if not Group().is_member_of_group(user, settings.PANOPTO_ADMIN_GROUP):
        return HttpResponseRedirect("/")

    status_code = 200

    try:
        term = get_current_term()
    except DataFailureException as ex:
        logger.exception(ex)
        raise StudentWebServiceUnavailable()

    t = loader.get_template(template)
    c = RequestContext(request, {
        'term_year': term.year,
        'term_quarter': term.quarter,
        'todays_date': time.strftime("%Y-%m-%d"),
        'canvas_host': settings.RESTCLIENTS_CANVAS_HOST if hasattr(
            settings, 'RESTCLIENTS_CANVAS_HOST') else '',
        'panopto_server': settings.PANOPTO_SERVER if hasattr(
            settings, 'PANOPTO_SERVER') else '',
        'STATIC_URL': settings.STATIC_URL,
    })

    return HttpResponse(t.render(c), status=status_code)
