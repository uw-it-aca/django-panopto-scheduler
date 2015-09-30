from scheduler.views.rest_dispatch import RESTDispatch
from panopto_client.remote_recorder import RemoteRecorderManagement
from restclients.r25.spaces import get_spaces, get_space_by_id
import logging


logger = logging.getLogger(__name__)


class Space(RESTDispatch):
    def __init__(self):
        self._api = RemoteRecorderManagement()
        # timeout in hours
        self._space_list_cache_timeout = 1

    def GET(self, request, **kwargs):
        space_id = kwargs.get('space_id')
        if (space_id):
            return self._get_space_details(space_id)
        else:
            params = {}
            for q in request.GET:
                params[q] = request.GET.get(q)

            return self._list_spaces(params)

    def _get_space_details(self, space_id):
        space = get_space_by_id(space_id)
        return self.json_response({
            'space_id': space.space_id,
            'name': space.name,
            'formal_name': space.formal_name
        })

    def _list_spaces(self, args):
        reps = []
        for space in get_spaces(**args):
            reps.append({
                'space_id': space.space_id,
                'name': space.name,
                'formal_name': space.formal_name
            })

        return self.json_response(reps)
