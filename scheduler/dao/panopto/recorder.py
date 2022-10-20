# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from scheduler.utils.validation import Validation
from panopto_client.remote_recorder import RemoteRecorderManagement
import re


recorder_api = RemoteRecorderManagement()


def list_recorders():
    return recorder_api.listRecorders()


def get_recorder_details(recorder_id):
    if re.match(r'^\d+$', recorder_id):
        recorders = get_recorder_by_external_id(recorder_id)
    else:
        Validation().panopto_id(recorder_id)
        recorders = get_recorder_by_id(recorder_id)

    if not (recorders and hasattr(recorders, 'RemoteRecorder')):
        return None

    return recorders.RemoteRecorder


def get_recorder_by_id(recorder_id):
    return recorder_api.getRemoteRecordersById(recorder_id)


def get_recorder_by_external_id(external_id):
    return recorder_api.getRemoteRecordersByExternalId(external_id)


def update_recorder_external_id(recorder_id, external_id):
    return recorder_api.updateRemoteRecorderExternalId(
        recorder_id, external_id)


def schedule_recording(
        name, folder_id, is_broadcast, start_time, end_time, recorder_id):
    return recorder_api.scheduleRecording(
        name, folder_id, is_broadcast, start_time, end_time, recorder_id)


def update_recording_time(session_id, start_time, end_time):
    return recorder_api.updateRecordingTime(session_id, start_time, end_time)
