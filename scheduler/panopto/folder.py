# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from scheduler.utils import local_ymd_from_utc_date_string
from scheduler.dao.panopto.access import get_folder_access_details
from scheduler.dao.panopto.user import get_users_from_guids
from scheduler.dao.panopto.sessions import get_folders_list
from hashlib import sha1
import re


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


def set_panopto_generic_folder(event):
    id_string = "{} - {}".format(event['name'], event['space']['id'])
    folder_name = event['name']
    folder_external_id = panopto_generic_external_id(id_string)
    creators = []

    folders = get_folders_list(search_query=event['name'])
    if folders and len(folders) == 1:
        folder_name = folders[0].Name
        folder_external_id = folders[0].ExternalId
        creators = get_panopto_folder_creators(folders[0].Id)

    event['recording']['folder']['name'] = folder_name
    event['recording']['folder']['external_id'] = folder_external_id
    event['recording']['folder']['auth'] = {'creators': creators}


def set_panopto_generic_session(event):
    name = "{} - {}".format(
        event['name'],
        local_ymd_from_utc_date_string(event['event']['start']))
    id_string = "{} - {}".format(name, event['space']['id'])
    event['recording']['name'] = name
    event['recording']['external_id'] = panopto_generic_external_id(id_string)
    event['recording']['is_public'] = False


def panopto_generic_external_id(id_string):
    return sha1(id_string.encode('utf-8')).hexdigest().upper()
