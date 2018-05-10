from django.conf import settings
from blti.views import BLTILaunchView


class CourseScheduleView(BLTILaunchView):
    template_name = 'scheduler/course.html'
    authorized_role = 'admin'

    def get_context_data(self, **kwargs):
        if self.blti.course_sis_id is not None:
            course_sis_id = self.blti.course_sis_id
        else:
            course_sis_id = 'course_%s' % self.blti.canvas_course_id

        return {
            'sis_course_id': course_sis_id,
            'canvas_host': getattr(settings, 'RESTCLIENTS_CANVAS_HOST', ''),
            'panopto_server': getattr(settings, 'PANOPTO_SERVER', ''),
            'session_id': self.request.session.session_key
        }

    def add_headers(self, **kwargs):
        response = kwargs.get('response')
        response['X-Frame-Options'] = ''
