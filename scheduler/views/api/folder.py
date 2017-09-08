from django.conf import settings
from scheduler.views.rest_dispatch import RESTDispatch
from panopto_client.session import SessionManagement
from panopto_client.access import AccessManagement
from panopto_client.user import UserManagement
import json
import re
import logging


logger = logging.getLogger(__name__)


class Folder(RESTDispatch):
    def _init_apis(self):
        self._session = SessionManagement()
        self._access = AccessManagement()
        self._user = UserManagement()

    def GET(self, request, **kwargs):
        folder_id = kwargs.get('folder_id')
        self._init_apis()
        if (folder_id):
            return self._get_folder_details(space_id)
        else:
            params = {}
            for q in request.GET:
                params[q] = request.GET.get(q)

            return self._list_folders(params)

    def _get_folder_details(self, space_id):
        return self.json_response('{}')

    def _list_folders(self, args):
        folders = []
        if 'search' in args:
            search = args['search'].strip()
            if len(search) > 3:
                for folder in self._session.getFoldersList(search_query=search):
                    creators = []
                    viewers = []
                    deets = self._access.getFolderAccessDetails(folder['Id'])
                    if deets.UsersWithCreatorAccess:
                        response = self._user.getUsers(deets.UsersWithCreatorAccess.guid)
                        if response and response.User:
                            for user in response.User:
                                match = re.match(r'^%s\\(.+)$' % (settings.PANOPTO_API_APP_ID), user.UserKey)
                                creators.append({
                                    'key': match.group(1) if match else user.UserKey,
                                    'id': user.UserId
                                })

                    if deets.UsersWithViewerAccess:
                        response = self._user.getUsers(deets.UsersWithCreatorAccess.guid)
                        if response and response.User:
                            for user in response.User:
                                match = re.match(r'^%s\\(.+)$' % (settings.PANOPTO_API_APP_ID), user.UserKey)
                                viewers.append({
                                    'key': match.group(1) if match else user.UserKey,
                                    'id': user.UserId
                                })

                    folders.append({
                        'name': folder.Name,
                        'id': folder.Id,
                        'auth' : {
                            'creators': creators,
                            'viewers': viewers
                        }
                    })

        return self.json_response(folders)
