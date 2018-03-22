from scheduler.views.rest_dispatch import RESTDispatch
from scheduler.utils.validation import Validation
from scheduler.views.api.exceptions import MissingParamException, \
    InvalidParamException
from panopto_client import PanoptoAPIException
from panopto_client.remote_recorder import RemoteRecorderManagement
from scheduler.models import RecorderCache, RecorderCacheEntry
from scheduler.utils.recorder import get_api_recorder_details, \
    RecorderException
from uw_r25.spaces import get_space_by_id
from restclients_core.exceptions import DataFailureException
import datetime
import logging
import json
import re
import pytz


logger = logging.getLogger(__name__)


class Recorder(RESTDispatch):
    def __init__(self):
        self._space_list_cache_timeout = 1  # timeout in hours

    def GET(self, request, **kwargs):
        self._api = RemoteRecorderManagement()
        recorder_id = kwargs.get('recorder_id')
        if request.GET.get('timeout'):
            self._space_list_cache_timeout = float(request.GET.get('timeout'))
        if (recorder_id):
            return self._get_recorder_details(recorder_id)
        else:
            return self._list_recorders()

    def PUT(self, request, **kwargs):
        recorder_id = kwargs.get('recorder_id')
        try:
            Validation().panopto_id(recorder_id)
            data = json.loads(request.body)
            external_id = data.get('external_id', None)
            self._api = RemoteRecorderManagement()
            if external_id is not None:
                rv = self._api.updateRemoteRecorderExternalId(recorder_id,
                                                              external_id)
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
            return self.error_response(400, message="%s" % err)

    def _get_recorder_details(self, recorder_id):
        try:
            recorders = get_api_recorder_details(self._api, recorder_id)
        except (RecorderException, PanoptoAPIException,
                MissingParamException, InvalidParamException) as err:
            return self.error_response(400, message="%s" % err)

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
                    space = get_space_by_id(recorders[0].ExternalId)
                    rep['space'] = {
                        'space_id': space.space_id,
                        'name': space.name,
                        'formal_name': space.formal_name
                    }
                except DataFailureException as err:
                    logger.error('Cannot get space for id: %s: %s' %
                                 (recorders[0].ExternalId, err))

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
                recorders = self._api.listRecorders()
                rec_cache = self._cache_recorders(recorders)
            except PanoptoAPIException as err:
                return self.error_response(400, message="%s" % err)

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
