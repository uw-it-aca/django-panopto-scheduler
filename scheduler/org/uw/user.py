# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from scheduler.user import BaseUser
import re


class User(BaseUser):

    uw_netid_re = r'^\s*([a-z][a-z0-9_]+)(@(uw|(u\.)?washington).edu)?\s*$'

    def validate_login_ids(self, login_ids):
        login_ids = []
        for rawid in login_ids:
            validated = self.validate_login_id(rawid)
            login_ids.append({
                'loginid': validated
            } if validated else {
                'loginid': rawid,
                'error': "Invalid UW Netid"
            })

        return login_ids

    def validate_login_id(self, login_id):
        match = re.match(self.uw_netid_re, login_id, re.I)
        return match.group(1).lower() if match else None
