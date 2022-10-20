# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from scheduler.views.rest_dispatch import RESTDispatch
from scheduler.dao.panopto.sessions import get_folders_list
from scheduler.dao.panopto.access import get_folder_access_details
from scheduler.dao.panopto.user import get_users_from_guids
import re
import logging


logger = logging.getLogger(__name__)


class Folder(RESTDispatch):
    def __init__(self, *args, **kwargs):
        super(Folder, self).__init__(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        params = {}
        for q in request.GET:
            params[q] = request.GET.get(q)

        return self._list_folders(params)

    def _list_folders(self, args):
        folders = []
        if 'search' in args:
            search = args['search'].strip()
            if len(search) > 3:
                for folder in get_folders_list(search_query=search):
                    creators = []
                    viewers = []
                    deets = get_folder_access_details(folder['Id'])
                    if deets.UsersWithCreatorAccess:
                        response = get_users_from_guids(
                            deets.UsersWithCreatorAccess.guid)
                        if response and response.User:
                            for user in response.User:
                                match = re.match(r'^{}\\(.+)$'.format(
                                    getattr(
                                        settings, 'PANOPTO_API_APP_ID', "")),
                                    user.UserKey)
                                creators.append({
                                    'key': match.group(1) if (
                                        match) else user.UserKey,
                                    'id': user.UserId
                                })

                    if deets.UsersWithViewerAccess:
                        response = get_users_from_guids(
                            deets.UsersWithCreatorAccess.guid)
                        if response and response.User:
                            for user in response.User:
                                match = re.match(r'^{}\\(.+)$'.format(
                                    getattr(
                                        settings, 'PANOPTO_API_APP_ID', '')),
                                    user.UserKey)
                                viewers.append({
                                    'key': match.group(1) if (
                                        match) else user.UserKey,
                                    'id': user.UserId
                                })

                    folders.append({
                        'name': folder.Name,
                        'id': folder.Id,
                        'auth': {
                            'creators': creators,
                            'viewers': viewers
                        }
                    })

        return self.json_response(folders)
