# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from scheduler.utils import local_ymd_from_utc_date_string
from scheduler.dao.panopto.access import get_folder_access_details
from scheduler.dao.panopto.user import get_users_from_guids
from scheduler.dao.panopto.sessions import (
    get_folders_with_external_context_list)
from hashlib import sha1
import logging
import re


logger = logging.getLogger(__name__)


def get_panopto_folder_creators(folder_id):
    creators = []
    folder_access = get_folder_access_details(folder_id)
    if ('UsersWithCreatorAccess' in folder_access and
            folder_access['UsersWithCreatorAccess'] and
            len(folder_access['UsersWithCreatorAccess'])):
        guids = folder_access['UsersWithCreatorAccess'][0]
        if len(guids):
            users = get_users_from_guids(guids)
            for user in users[0]:
                match = re.match(
                    r'^{}\\(.+)$'.format(
                        settings.PANOPTO_API_APP_ID), user['UserKey'])
                if match:
                    creators.append(
                        match.group(1) if match else user['UserKey'])

    return creators


def panopto_folder_id(event_folder):
    try:
        if event_folder['id']:
            return event_folder['id']

        folder_name = event_folder['name']
        if not folder_name:
            return None

    except KeyError:
        return None

    creators = []

    folders = get_folders_with_external_context_list(
        search_query=folder_name)

    if folders:
        if len(folders) == 1:
            return folders[0].Id
        else:
            logger.info(
                "panopto_folder_id: many folders named {}".format(
                    folder_name))
            for f in folders:
                logger.info("folder name '{}', Id: {}, ExternalId".format(
                    f.Name, f.Id, f.ExternalId))

    return None
