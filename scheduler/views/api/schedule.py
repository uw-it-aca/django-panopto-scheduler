# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from scheduler.views.rest_dispatch import RESTDispatch
from scheduler.views.api.exceptions import MissingParamException, \
    InvalidParamException
from scheduler.utils import space_events_and_recordings
from scheduler.utils import course_location_and_recordings, \
    CourseEventException
from scheduler.utils.validation import Validation
from restclients_core.exceptions import DataFailureException
import logging


logger = logging.getLogger(__name__)


class Schedule(RESTDispatch):
    def get(self, request, *args, **kwargs):
        try:
            course = Validation().course_id(kwargs['course_id'])
            events = course_location_and_recordings(course)
        except MissingParamException as ex:
            events = space_events_and_recordings(request.GET)
        except CourseEventException as ex:
            return self.error_response(404, message=ex)
        except InvalidParamException as ex:
            return self.error_response(400, message=ex)
        except DataFailureException as ex:
            return self.error_response(ex.status, message=ex)
        except Exception as ex:
            logger.exception(ex)
            return self.error_response(500, message=ex)

        return self.json_response(events)

    def post(self, request, *args, **kwargs):
        session_ids = request.data.get('session_ids', [])
        events = space_events_and_recordings({
            'session_ids': session_ids
        })
        return self.json_response(events)
