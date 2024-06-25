# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from scheduler.views.rest_dispatch import RESTDispatch
from scheduler.dao.panopto.sessions import get_folders_list, get_folders_by_id
from scheduler.dao.panopto.access import get_folder_access_details
from scheduler.dao.panopto.user import get_users_from_guids
from scheduler.exceptions import PanoptoFolderDoesNotExist
import re
import logging


logger = logging.getLogger(__name__)

# to prevent too many results
MIN_SEARCH_LENGTH = 4


class Folder(RESTDispatch):
    def get(self, request, *args, **kwargs):
        try:
            if kwargs.get('folder_id'):
                return self.json_response(
                    self._get_folder_details(kwargs.get('folder_id')))

            params = {}
            for q in request.GET:
                params[q] = request.GET.get(q)

            return self.json_response(self._get_folder_list(params))
        except PanoptoFolderDoesNotExist as ex:
            return self.error_response(404, message=ex)
        except Exception as ex:
            logger.exception(ex)
            return self.error_response(500, message=ex)

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except Exception as ex:
            logger.exception(ex)
            return self.error_response(500, message=ex)

    def _get_folder_list(self, args):
        folders = []
        if 'search' in args:
            search = args['search'].strip()
            if len(search) > MIN_SEARCH_LENGTH:
                for folder in get_folders_list(search_query=search):
                    if folder.ParentFolder:
                        self._insert_parent(
                            folders, folder.ParentFolder, self._folder(folder))
                    else:
                        folders.append(self._folder(folder))

        return folders

    def _insert_parent(self, folders, parent_id, child):
        parent = self._find_parent(folders, parent_id)
        if parent:
            self._add_child(parent, child)
        else:
            parent = self._folder(self._get_folder_by_id(folder_id))
            self._add_child(parent, child)
            if parent['parent_folder_id']:
                self._insert_parent(
                    folders, parent['parent_folder_id'], parent)
            else:
                folders.append(parent)

    def _find_parent(self, folders, parent_id):
        for folder in folders:
            if folder.get('id') == parent_id:
                return folder
            else:
                for i, child in enumerate(folder['child_folders']):
                    if child.get('id') == parent_id:
                        return child
                    elif child.get('guid') == parent_id:
                        folder['child_folders'][i] = self._folder(
                            self._get_folder_by_id(parent_id))
                        return folder['child_folders'][i]

    def _add_child(self, parent, child):
        for i, folder in enumerate(parent['child_folders']):
            if folder.get('guid') == child.get('id'):
                parent['child_folders'][i] = child
                return

        raise Exception("Inconsistent parent child relationship")

    def _folder(self, folder):
        return {
            'name': folder.Name,
            'id': folder.Id,
            'parent_folder_id': None,
            'child_folders': [{'guid': guid} for (guid) in getattr(
                folder.ChildFolders, 'guid', [])]
        }

    def _get_folder_details(self, folder_id):
        folder = self._get_folder_by_id(folder_id)
        creators = []
        viewers = []
        deets = get_folder_access_details(folder['id'])
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

        return self._folder(folder).update({
            'auth': {
                'creators': creators,
                'viewers': viewers
            }
        })

    def _get_folder_by_id(self, folder_id):
        folders = get_folders_by_id([folder_id])
        if folders and len(folders) == 1:
            return folders[0]

        raise Exception("Unexpected get_folder_by_id response")
