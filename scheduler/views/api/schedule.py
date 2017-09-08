from scheduler.views.rest_dispatch import RESTDispatch
from scheduler.views.api.exceptions import MissingParamException, \
    InvalidParamException
from scheduler.utils import space_events_and_recordings
from scheduler.utils import course_location_and_recordings, \
    CourseEventException
from scheduler.utils.validation import Validation
from restclients_core.exceptions import DataFailureException
import logging
import re


logger = logging.getLogger(__name__)


class Schedule(RESTDispatch):
    def GET(self, request, **kwargs):
        try:
            course = Validation().course_id(kwargs['course_id'])
            events = course_location_and_recordings(course)
        except MissingParamException as ex:
            events = space_events_and_recordings(request.GET)
        except CourseEventException as ex:
            return self.error_response(404, message=str(ex))
        except InvalidParamException as ex:
            return self.error_response(400, message=str(ex))
        except DataFailureException as ex:
            return self.error_response(ex.status, str(ex))
        except Exception as ex:
            logger.exception(ex)
            return self.error_response(500, str(ex))

        return self.json_response(events)
