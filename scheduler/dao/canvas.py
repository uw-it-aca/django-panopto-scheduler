# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from uw_canvas.courses import Courses as CanvasCourses


canvas_api = CanvasCourses()


def get_course_by_sis_id(sis_id):
    return canvas_api.get_course_by_sis_id(sis_id)


def get_course_by_canvas_id(course_id):
    if canvas_api.valid_course_id(course_id):
        return canvas_api.get_course(course_id)

    raise Exception("Invalid course id: {}".format(course_id))
