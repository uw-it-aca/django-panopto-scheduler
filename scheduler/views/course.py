from django.conf import settings
from django.template import Context, loader
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.context_processors import csrf
from blti import BLTI, BLTIException
from scheduler.utils import course_location_and_recordings, \
    CourseEventException
from scheduler.utils.validation import Validation
import json


@csrf_exempt
def CourseSchedule(request, template='scheduler/course.html'):
    blti_data = {
        "context_label": "NO COURSE"
    }
    validation_error = None
    sis_course_id = 'None'
    canvas_course_id = 'None'
    canvas_login_id = 'None'
    status_code = 200
    try:
        blti = BLTI()
        blti_data = blti.validate(request)
        canvas_login_id = blti_data.get('custom_canvas_user_login_id')
        canvas_course_id = blti_data.get('custom_canvas_course_id')
        sis_course_id = blti_data.get('lis_course_offering_sourcedid',
                                      'course_%s' % canvas_course_id)
        blti.set_session(request,
                         user_id=canvas_login_id,
                         canvas_course_id=canvas_course_id,
                         sis_course_id=sis_course_id)
    except CourseEventException as err:
        validation_error = err
        template = 'scheduler/lti_fail.html'
        status_code = 404
    except BLTIException, err:
        validation_error = err
        template = 'scheduler/lti_fail.html'
        status_code = 401
    except Exception, err:
        validation_error = err
        template = 'scheduler/lti_fail.html'
        status_code = 400

    t = loader.get_template(template)
    c = Context({
        'SIS_COURSE_ID': sis_course_id,
        'CANVAS_LOGIN_ID': canvas_login_id,
        'CANVAS_COURSE_ID': canvas_course_id,
        'VALIDATION_ERROR': validation_error,
        'canvas_host': settings.RESTCLIENTS_CANVAS_HOST if hasattr(
            settings, 'RESTCLIENTS_CANVAS_HOST') else '',
        'panopto_server': settings.PANOPTO_SERVER if hasattr(
            settings, 'PANOPTO_SERVER') else '',
        'session_id': request.session.session_key
    })

    c.update(csrf(request))
    response = HttpResponse(t.render(c), status=status_code)
    response["X-Frame-Options"] = ""
    return response
