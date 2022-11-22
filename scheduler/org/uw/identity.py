# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from scheduler.user import BaseUser
import re


class User(BaseUser):

    UW_DOMAINS = ['uw.edu', 'washington.edu', 'u.washington.edu']

    def get_loginid_from_email(self, email):
        match = re.match(
            r'^([a-z][0-9a-z]{{0,7}})@({})$'.format('|'.join(self.UW_DOMAINS)),
            email)
        return match.group(1) if match else ""
