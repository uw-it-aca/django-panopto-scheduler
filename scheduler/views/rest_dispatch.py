from django.conf import settings
from authz_group import Group
from blti.views.rest_dispatch import RESTDispatch as BLTIRESTDispatch,\
    RESTDispatchAuthorization


class RESTDispatch(BLTIRESTDispatch):
    """ Handles passing on the request to the correct view method
        based on the request type.
    """
    def authorize(self, request):
        try:
            super(RESTDispatch, self).authorize(request)
        except RESTDispatchAuthorization as err:
            if (request.user.is_authenticated() and
                Group().is_member_of_group(
                    request.user.username,
                    getattr(settings, 'PANOPTO_ADMIN_GROUP'))):
                return

            raise RESTDispatchAuthorization('Access Denied')
