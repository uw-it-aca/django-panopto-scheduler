# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from scheduler.views.rest_dispatch import RESTDispatch
from scheduler.exceptions import (
    MissingParamException, InvalidParamException, CourseReservationsException)
from scheduler.schedule import (
    space_events_and_recordings, course_location_and_recordings)
from restclients_core.exceptions import DataFailureException
import json
import logging


logger = logging.getLogger(__name__)


class Schedule(RESTDispatch):
    def get(self, request, *args, **kwargs):
        try:
            schedule = course_location_and_recordings(kwargs.get('course_id'))
        except MissingParamException as ex:
            schedule = space_events_and_recordings(request.GET)
        except CourseReservationsException as ex:
            return self.error_response(404, message=ex)
        except InvalidParamException as ex:
            return self.error_response(400, message=ex)
        except DataFailureException as ex:
            return self.error_response(ex.status, message=ex)
        except Exception as ex:
            logger.exception(ex)
            return self.error_response(500, message=ex)

        return self.json_response(schedule)

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        session_ids = data.get('session_ids', [])
        schedule = space_events_and_recordings({
            'session_ids': session_ids
        })
        return self.json_response(schedule)
