from django.conf import settings
from authz_group import Group
from blti.views import RESTDispatch as BLTIRESTDispatch, BLTIException


class RESTDispatch(BLTIRESTDispatch):
    authorized_role = 'admin'

    def validate(self, request):
        try:
            super(RESTDispatch, self).validate(request)
        except BLTIException:
            if not (request.user.is_authenticated() and
                    Group().is_member_of_group(request.user.username,
                                               settings.PANOPTO_ADMIN_GROUP)):
                raise
