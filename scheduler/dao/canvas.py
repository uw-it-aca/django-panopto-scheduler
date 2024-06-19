# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from uw_canvas.courses import Courses as CanvasCourses
from scheduler.utils import timer


canvas_api = CanvasCourses()


@timer
def get_course_by_sis_id(sis_id):
    return canvas_api.get_course_by_sis_id(sis_id)


@timer
def get_course_by_canvas_id(course_id):
    if canvas_api.valid_course_id(course_id):
        return canvas_api.get_course(course_id)

    raise Exception("Invalid course id: {}".format(course_id))
