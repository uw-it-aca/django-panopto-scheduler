# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from scheduler.utils.validation import Validation
from panopto_client.remote_recorder import RemoteRecorderManagement
from scheduler.utils import timer
import re


recorder_api = RemoteRecorderManagement()


@timer
def list_recorders():
    return recorder_api.listRecorders()


@timer
def get_recorder_details(recorder_id):
    if re.match(r'^\d+$', recorder_id):
        recorders = get_recorder_by_external_id(recorder_id)
    else:
        Validation().panopto_id(recorder_id)
        recorders = get_recorder_by_id(recorder_id)

    if not (recorders and hasattr(recorders, 'RemoteRecorder')):
        return None

    return recorders.RemoteRecorder


@timer
def get_recorder_by_id(recorder_id):
    return recorder_api.getRemoteRecordersById(recorder_id)


@timer
def get_recorder_by_external_id(external_id):
    return recorder_api.getRemoteRecordersByExternalId(external_id)


@timer
def update_recorder_external_id(recorder_id, external_id):
    return recorder_api.updateRemoteRecorderExternalId(
        recorder_id, external_id)


@timer
def schedule_recording(
        name, folder_id, is_broadcast, start_time, end_time, recorder_id):
    return recorder_api.scheduleRecording(
        name, folder_id, is_broadcast, start_time, end_time, recorder_id)


@timer
def update_recording_time(session_id, start_time, end_time):
    return recorder_api.updateRecordingTime(session_id, start_time, end_time)
