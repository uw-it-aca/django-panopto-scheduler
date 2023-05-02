# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from uw_canvas.courses import Courses as CanvasCourses


def get_course_by_sis_id(sis_id):
    return CanvasCourses().get_course_by_sis_id(sis_id)
