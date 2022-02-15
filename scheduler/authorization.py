# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from uw_saml.utils import is_member_of_group
import re


def userservice_validate(username):
    if len(username) == 0:
        return "No override user supplied"

    if username != username.lower():
        return "Usernames must be all lowercase"

    re_personal_netid = re.compile(r'^[a-z][a-z0-9]{0,7}$', re.I)
    if not re_personal_netid.match(username):
        return ("Username not a valid netid (starts with a letter, "
                "then 0-7 letters or numbers)")

    return None


def can_view_source_data(request, service=None, url=None):
    return is_member_of_group(request, settings.RESTCLIENTS_ADMIN_GROUP)
