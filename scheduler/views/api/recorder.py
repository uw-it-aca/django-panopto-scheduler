# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from scheduler.views.rest_dispatch import RESTDispatch
from scheduler.utils.validation import Validation
from scheduler.exceptions import (
    MissingParamException, InvalidParamException, RecorderException)
from scheduler.dao.panopto.recorder import (
    get_recorder_details, update_recorder_external_id, list_recorders)
from scheduler.reservations import Reservations
from scheduler.models import RecorderCache, RecorderCacheEntry
from panopto_client import PanoptoAPIException
from restclients_core.exceptions import DataFailureException
import datetime
import logging
import json
import pytz


logger = logging.getLogger(__name__)


class Recorder(RESTDispatch):
    def __init__(self, *args, **kwargs):
        self._space_list_cache_timeout = 1  # timeout in hours
        self.reservations = Reservations()
        super(Recorder, self).__init__(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        recorder_id = kwargs.get('recorder_id')
        if request.GET.get('timeout'):
            self._space_list_cache_timeout = float(request.GET.get('timeout'))
        if (recorder_id):
            return self._get_recorder_details(recorder_id)
        else:
            return self._list_recorders()

    def put(self, request, *args, **kwargs):
        recorder_id = kwargs.get('recorder_id')
        try:
            Validation().panopto_id(recorder_id)
            data = json.loads(request.body)
            external_id = data.get('external_id', None)
            if external_id is not None:
                update_recorder_external_id(recorder_id, external_id)
                try:
                    cache_entry = RecorderCacheEntry.objects.get(
                        recorder_id=recorder_id)
                    cache_entry.recorder_external_id = external_id
                    cache_entry.save()
                except RecorderCacheEntry.DoesNotExist:
                    pass

            return self._get_recorder_details(recorder_id)
        except (MissingParamException, InvalidParamException,
                PanoptoAPIException) as err:
            return self.error_response(400, message="{}".format(err))

    def _get_recorder_details(self, recorder_id):
        try:
            recorders = get_recorder_details(recorder_id)
        except (RecorderException, PanoptoAPIException,
                MissingParamException, InvalidParamException) as err:
            return self.error_response(400, message="{}".format(err))

        if recorders is None:
            return self.error_response(404, message="No Recorder Found")

        return self._recorder_rep(recorders)

    def _recorder_rep(self, recorders):
        reps = []
        for recorder in recorders:
            rep = {
                'id': recorder.Id,
                'external_id': recorder.ExternalId,
                'name': recorder.Name,
                'settings_url': recorder.SettingsUrl,
                'state': recorder.State,
                'space': None,
                'scheduled_recordings': []
            }

            if recorder.ScheduledRecordings and hasattr(
                    recorder.ScheduledRecordings, 'guid'):
                for recording in recorder.ScheduledRecordings.guid:
                    rep['scheduled_recordings'].append(recording)

            if recorder.ExternalId:
                try:
                    space = self.reservations.get_space_by_id(
                        recorders[0].ExternalId)
                    rep['space'] = {
                        'space_id': space.space_id,
                        'name': space.name,
                        'formal_name': space.formal_name
                    }
                except DataFailureException as err:
                    logger.error('Cannot get space for id: {}: {}'.format(
                        recorders[0].ExternalId, err))

            reps.append(rep)

        return self.json_response(reps)

    def _list_recorders(self):
        try:
            rec_cache = RecorderCache.objects.all()[0]
            now = pytz.UTC.localize(datetime.datetime.now())
            timeout = datetime.timedelta(hours=self._space_list_cache_timeout)
            if (now - timeout) > rec_cache.created_date:
                self._scrub_recorder_cache(rec_cache)

        except (IndexError, RecorderCache.DoesNotExist):
            try:
                recorders = list_recorders()
                rec_cache = self._cache_recorders(recorders)
            except PanoptoAPIException as err:
                return self.error_response(400, message="{}".format(err))

        rep = []
        for recorder in RecorderCacheEntry.objects.filter(cache=rec_cache):
            rep.append({
                'id': recorder.recorder_id,
                'external_id': recorder.recorder_external_id,
                'name': recorder.name,
                'scheduled_recordings': []
            })

        return self.json_response(rep)

    def _cache_recorders(self, recorders):
        rec_cache = RecorderCache()
        rec_cache.save()
        for recorder in recorders:
            RecorderCacheEntry.objects.create(
                cache=rec_cache,
                recorder_id=recorder.Id,
                recorder_external_id=recorder.ExternalId or '',
                name=recorder.Name)

        return rec_cache

    def _scrub_recorder_cache(self, rec_cache):
        RecorderCacheEntry.objects.filter(cache=rec_cache).delete()
        rec_cache.delete()
        raise RecorderCache.DoesNotExist()
