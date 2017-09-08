from django.conf import settings
from authz_group import Group
from blti.validators import BLTIOauth, BLTIException
from blti.views.rest_dispatch import RESTDispatch as BLTIRESTDispatch
from blti.views.rest_dispatch import RESTDispatchAuthorization


class RESTDispatch(BLTIRESTDispatch):
    """ Handles passing on the request to the correct view method
        based on the request type.
    """
    def authorize(self, request):
        try:
            self.blti_authorize(request)
        except RESTDispatchAuthorization:
            try:
                BLTIOauth().validate(request)
            except BLTIException:
                if (request.user.is_authenticated() and
                    Group().is_member_of_group(
                        request.user.username,
                        settings.PANOPTO_ADMIN_GROUP)):
                    return

                raise RESTDispatchAuthorization("Access Denied")
