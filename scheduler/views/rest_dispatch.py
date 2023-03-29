# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from uw_saml.utils import is_member_of_group
from blti.views import RESTDispatch as BLTIRESTDispatch, BLTIException


class RESTDispatch(BLTIRESTDispatch):
    authorized_role = 'admin'

    def validate(self, request):
        try:
            super(RESTDispatch, self).validate(request)
        except BLTIException:
            if not is_member_of_group(request, settings.PANOPTO_ADMIN_GROUP):
                raise
