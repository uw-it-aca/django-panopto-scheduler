# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from uw_gws import GWS


def email_addresses_from_group(group_name):
    email = []
    gws = GWS()

    for member in gws.get_effective_members(group_name):
        if member.is_uwnetid():
            email.append("{}@uw.edu".format(member.name))

    return email
