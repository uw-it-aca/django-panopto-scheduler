# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from uw_gws import GWS


def email_addresses_from_group(group_name):
    email = []
    gws = GWS()

    for netid in gws.get_effective_members(group_name):
        email.append("{}.uw.edu".format(netid))

    return email
