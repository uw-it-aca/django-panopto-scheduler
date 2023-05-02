# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from scheduler.utils.validation import Validation
from panopto_client.remote_recorder import RemoteRecorderManagement
import re


class RecorderException(Exception):
    pass


def get_recorder_details(recorder_id):
    return get_api_recorder_details(RemoteRecorderManagement(), recorder_id)


def get_api_recorder_details(api, recorder_id):
    if re.match(r'^\d+$', recorder_id):
        recorders = api.getRemoteRecordersByExternalId(recorder_id)
    else:
        Validation().panopto_id(recorder_id)
        recorders = api.getRemoteRecordersById(recorder_id)

    if not (recorders and hasattr(recorders, 'RemoteRecorder')):
        return None

    return recorders.RemoteRecorder
