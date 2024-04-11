# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from scheduler.exceptions import (
    MissingParamException, InvalidParamException)
import re


class Validation(object):
    """  Validates Panopto Id format and various course parameters
    """
    def panopto_id(self, id):
        if not re.match(r'^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$', id):
            raise InvalidParamException(
                'Invalid Panopto Id: {}'.format(id))

        return id
