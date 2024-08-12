# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from scheduler.views.rest_dispatch import RESTDispatch
from scheduler.dao.panopto.sessions import (
    get_folders_list, get_folders_by_id, add_folder)
from scheduler.dao.panopto.access import get_folder_access_details
from scheduler.dao.panopto.user import get_users_from_guids
from scheduler.utils.validation import Validation
from scheduler.exceptions import (
    PanoptoFolderDoesNotExist, PanoptoFolderSearchTooShort,
    MissingParamException)
import json
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
            folders = []

            data = json.loads(request.body)
            folder_name = self._valid_folder_name(
                data.get('folder_name')),
            parent_folder_id = self._valid_parent_folder_id(
                data.get('parent_folder_id'))

            folder_response = get_folders_list(
                search_query=folder_name, parent_folder_id=parent_folder_id)

            if folder_response:
                if len(folder_response) > 1:
                    self.error_response(409, message="Folders already exist")

                self._insert_folder(folders, self._folder(folder_response))
                return self.json_response(folders, status=200)

            folder_response = add_folder(folder_name, parent_folder_id)
            if folder_response:
                self._insert_folder(folders, self._folder(folder_response))
                return self.json_response(folders, status=201)

            return self.error_response(
                404, message="Folder not created")
        except Exception as ex:
            logger.exception(ex)
            return self.error_response(500, message=ex)

    def _get_folder_list(self, args):
        folders = []
        params = {}

        if 'search' in args:
            search = args['search'].strip()
            if len(search) < MIN_SEARCH_LENGTH:
                raise PanoptoFolderSearchTooShort(
                    f"Must be at least {MIN_SEARCH_LENGTH} characters")

            params['search_query'] = search

            if 'parent_folder_id' in args and args['parent_folder_id']:
                params['parent_folder_id'] = args['parent_folder_id']

            for folder in get_folders_list(**params):
                self._insert_folder(folders, self._folder(folder))

        return folders

    def _insert_folder(self, folders, folder):
        parent_id = folder.get('parent_folder_id')
        if parent_id:
            parent = self._find_folder(folders, parent_id)
            if parent:
                self._add_child(parent, folder)
            else:
                parent = self._folder(self._get_folder_by_id(parent_id))
                self._add_child(parent, folder)
                self._insert_folder(folders, parent)
        else:
            folders.append(folder)

    def _find_folder(self, folders, parent_id):
        for i, folder in enumerate(folders if folders else []):
            if parent_id == folder.get('id'):
                return folder

            folder_id = folder.get('guid')
            if parent_id == folder_id:
                folders[i] = self._folder(self._get_folder_by_id(parent_id))
                return folders[i]

            found = self._find_folder(folder.get('child_folders'), parent_id)
            if found:
                return found

        return None

    def _add_child(self, parent, child):
        for i, folder in enumerate(parent['child_folders']):
            if folder.get('guid') == child.get('id'):
                parent['child_folders'][i] = child
                return

            if folder.get('id') == child.get('id'):
                return

        raise Exception("Inconsistent parent child relationship")

    def _folder(self, folder):
        return {
            'name': folder.Name,
            'id': folder.Id,
            'parent_folder_id': folder.ParentFolder,
            'child_folders': [{'guid': guid} for (
                guid) in getattr(folder.ChildFolders, 'guid', [])]
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
            return folders[0][0]

        raise Exception("Unexpected get_folder_by_id response")

    def _valid_folder_name(self, folder_name):
        if not folder_name:
            raise MissingParamException("folder_name is required")

        return folder_name

    def _valid_parent_folder_id(self, parent_folder_id):
        return Validation().panopto_id(parent_folder_id) if (
            parent_folder_id) else None
