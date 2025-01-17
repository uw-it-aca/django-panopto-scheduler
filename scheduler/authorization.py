# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from uw_saml.utils import is_member_of_group
from scheduler.user import User


def userservice_validate(username):
    if len(username) == 0:
        return "No override user supplied"

    if username != username.lower():
        return "Usernames must be all lowercase"

    if not User().validate_login_id(username):
        return ("Username not a valid netid (starts with a letter, "
                "then 0-7 letters or numbers)")

    return None


def can_view_source_data(request, service=None, url=None):
    return is_member_of_group(request, settings.RESTCLIENTS_ADMIN_GROUP)
