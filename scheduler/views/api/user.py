# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from scheduler.views.rest_dispatch import RESTDispatch
from scheduler.user import User
import json
import logging


logger = logging.getLogger(__name__)


class UserValidation(RESTDispatch):
    def __init__(self):
        self.user = User()

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        login_ids = data.get('login_ids', [])
        validated = User().validate_login_ids(login_ids)
        return self.json_response(validated)
