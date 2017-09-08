from django.conf import settings
from blti.views import BLTILaunchView


class CourseScheduleView(BLTILaunchView):
    template_name = 'scheduler/course.html'
    authorized_role = 'admin'

    def get_context_data(self, **kwargs):
        request = kwargs.get('request')
        blti_data = kwargs.get('blti_params')
        canvas_course_id = blti_data.get('custom_canvas_course_id')

        return {
            'sis_course_id': blti_data.get('lis_course_offering_sourcedid',
                                           'course_%s' % canvas_course_id),
            'canvas_host': getattr(settings, 'RESTCLIENTS_CANVAS_HOST', ''),
            'panopto_server': getattr(settings, 'PANOPTO_SERVER', ''),
            'session_id': request.session.session_key
        }

    def add_headers(self, **kwargs):
        response = kwargs.get('response')
        response['X-Frame-Options'] = ''
