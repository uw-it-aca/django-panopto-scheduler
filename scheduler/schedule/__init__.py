# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from restclients_core.exceptions import DataFailureException
from scheduler.utils import schedule_key
from scheduler.dao.r25 import (
    get_event_by_course, get_reservations_by_search_params)
from scheduler.panopto.folder import (
    get_panopto_folder_creators, set_panopto_generic_folder,
    set_panopto_generic_session)
from scheduler.dao.panopto.recorder import get_recorder_details
from scheduler.dao.panopto.sessions import (
    get_sessions_by_external_ids, get_sessions_by_session_ids)
from scheduler.dao.panopto.access import get_session_access_details
from scheduler.exceptions import CourseEventException
from panopto_client import PanoptoAPIException
from dateutil import parser, tz
from importlib import import_module
import datetime
import pytz
import logging
import re


logger = logging.getLogger(__name__)
UW_DOMAIN = ['uw.edu', 'washington.edu', 'u.washington.edu']
UW_MEETING_TYPES = ['lecture', 'seminar', 'quiz', 'lab', 'final']


def course_location_and_recordings(course):
    try:
        event = get_event_by_course(course)
        return course_recording_sessions(course, event)
    except PanoptoAPIException as err:
        raise CourseEventException(
            "There was a problem connecting to the Panopto server. {}".format(
                err))
    except Exception as ex:
        logger.exception(ex)
        raise CourseEventException("Data Failure: {}".format(ex))


def course_recording_sessions(course, event):
    event_sessions = []
    recorders = {}
    session_external_ids = []
    joint = []

    # cross listed?
    if len(event.binding_reservations):
        course = course.get_crosslisted_course()

    contact = course.course_event_title_and_contact()
    folder = course.panopto_course_folder(contact['title_long'])
    for rsv in event.reservations:

        event_session = event_session_from_reservation(rsv)

        if event_session['profile'].split()[-1].lower() in ['lab', 'final']:
            continue

        event_session['joint'] = joint if len(joint) else None

        event_session['recording']['folder'] = folder

        name, external_id = course.panopto_course_session(rsv.start_datetime)
        event_session['recording']['name'] = name
        event_session['recording']['external_id'] = external_id

        space_id = rsv.space_reservation.space_id if (
            rsv.space_reservation) else None

        if space_id and space_id not in recorders:
            recorders[space_id] = get_recorder_id_for_space_id(space_id)

        session_external_ids.append(external_id)

        event_session['schedulable'] = True if (
            folder['external_id'] and event_session['space']['id']) else False

        event_session['contact'] = contact

        event_sessions.append(event_session)

    mash_in_panopto_sessions(event_sessions, session_external_ids, recorders)

    return event_sessions


def space_events_and_recordings(params):
    search = {
        'space_id': params.get('space_id'),
        'start_dt': params.get('start_dt'),
        'session_ids': params.get('session_ids'),
    }

    event_sessions = []
    event_external_ids = []
    recorders = {
        search['space_id']: params.get('recorder_id')
    }

    if search['session_ids']:
        ids = search['session_ids'] if isinstance(
            search['session_ids'], list) else search['session_ids'].split(',')
        sessions = get_sessions_by_session_ids(ids)

        for s in sessions:
            event_session = event_session_from_scheduled_recording(s)
            event_sessions.append(event_session)

        return event_sessions

    if search['space_id'] and search['start_dt']:
        try:
            reservations = get_reservations_by_search_params(search)
        except DataFailureException as ex:
            if ex.status == 404:
                reservations = []
            else:
                raise

        # build event sessions, accounting for joint class reservations
        for r in reservations:
            event_session = event_session_from_reservation(r)

            for s in event_sessions:
                if event_session['recording'][
                        'start'] == s['recording']['start']:
                    if isinstance(s['name'], list):
                        s['name'].append(event_session['name'])
                        s['name'].sort()
                    else:
                        s['name'] = [s['name'], event_session['name']]

                    event_session = None
                    break

            if event_session:
                event_sessions.append(event_session)

        # overlay session data
        for event_session in list(event_sessions):
            # remove academic courses and generate external_id
            if ('profile' in event_session and
                    event_session['profile'] and
                    event_session['profile'].lower() in UW_MEETING_TYPES):
                event_sessions.remove(event_session)
            else:
                set_panopto_generic_folder(event_session)
                set_panopto_generic_session(event_session)
                event_external_ids.append(
                    event_session['recording']['external_id'])

    mash_in_panopto_sessions(event_sessions, event_external_ids, recorders)

    return event_sessions


def event_session_from_reservation(r):
    session = {
        'profile': r.profile_name if (hasattr(r, 'profile_name') and
                                      r.profile_name) else '',
        'name': r.event_name,
        'schedulable': True,
        'space': {
            'id': None,
            'name': None,
            'formal_name': None
        },
        'recording': {
            'name': None,
            'id': None,
            'external_id': None,
            'recorder_id': None,
            'start': None,
            'end': None,
            'folder': {
                'name': None,
                'id': None,
                'external_id': None
            }
        },
        'contact': {
            'name': r.contact_name,
            'uwnetid': None,
            'email': r.contact_email if r.contact_email else ''
        }
    }

    if hasattr(r, 'space_reservation'):
        if r.space_reservation:
            session['space']['id'] = r.space_reservation.space_id
            session['space']['name'] = r.space_reservation.name
            session['space']['formal_name'] = r.space_reservation.formal_name
        else:
            logger.error(
                "Meeting for {} on {} has no space reservation ".format(
                    r.event_name, r.start_datetime))

    match = re.match(
        r'^([a-z][0-9a-z]{{0,7}})@({})$'.format('|'.join(UW_DOMAIN)),
        session['contact']['email'])
    if match:
        session['contact']['uwnetid'] = match.group(1)

    start_dt = parser.parse(r.start_datetime)
    end_dt = parser.parse(r.end_datetime) + \
        datetime.timedelta(seconds=int(
            getattr(settings, 'DEFAULT_RECORDING_TIME_FUDGE', 120)))
    start_utc = start_dt.astimezone(tz.tzutc())
    end_utc = end_dt.astimezone(tz.tzutc())

    session['event'] = {}
    session['event']['start'] = start_utc.isoformat()
    session['event']['end'] = end_utc.isoformat()

    session['recording']['start'] = start_utc.isoformat()
    session['recording']['end'] = end_utc.isoformat()

    return session


def event_session_from_scheduled_recording(s):
    start_utc = s.StartTime.astimezone(pytz.utc)
    end_utc = start_utc + datetime.timedelta(seconds=int(s.Duration))

    session = {
        'profile': '',
        'name': s.Name,
        'schedulable': True,
        'space': {
            'id': None,
            'name': None,
            'formal_name': None
        },
        'recording': {
            'name': s.Name,
            'id': s.Id,
            'external_id': s.ExternalId,
            'recorder_id': s.RemoteRecorderIds.guid[0],
            'start': start_utc.isoformat(),
            'end': end_utc.isoformat(),
            'folder': {
                'name': s.FolderName,
                'id': s.FolderId,
                'external_id': s.FolderId,
            },
            'is_broadcast': s.IsBroadcast
            #  property below is added conditionally for events
            #  'is_public': False,
        },
        'contact': {
            'name': '',
            'uwnetid': '',
            'email': '',
        },
        'event': {
            'start': start_utc.isoformat(),
            'end': end_utc.isoformat(),
        }
    }

    session['key'] = schedule_key(
        session['contact']['uwnetid'], session['recording']['name'],
        session['recording']['external_id'],
        session['recording']['recorder_id'], session['event']['start'],
        session['event']['end'])

    return session


def mash_in_panopto_sessions(event_sessions, session_external_ids, recorders):
    # mash in panopto recorder schedule
    session_access = {}
    if len(session_external_ids):
        sessions = get_sessions_by_external_ids(session_external_ids)
        for session in sessions if sessions else []:
            for e in event_sessions:
                e_r = e['recording']

                # only do the work of getting details if they're requested
                if 'is_public' in e_r and session.Id not in session_access:
                    details = get_session_access_details(session.Id)
                    session_access[session.Id] = details

                if session.ExternalId == e_r['external_id']:
                    start_time = parser.parse(e_r['start'])
                    end_time = parser.parse(e_r['end'])
                    if not (start_time <= session.StartTime and
                            end_time >= session.StartTime):
                        continue

                    e_r['recorder_id'] = session.RemoteRecorderIds.guid[0] if (
                        hasattr(session.RemoteRecorderIds, 'guid')) else None

                    # validate recorder id
                    e_r['relocated_recorder_id'] = None
                    if (e['space']['id'] and e['space']['id'] in recorders and
                            recorders[e['space']['id']] != e_r['recorder_id']):
                        e_r['relocated_recorder_id'] = recorders[
                            e['space']['id']]
                        logger.info(
                            ('Stale session recorder id: {}, '
                             'session: "{}", '
                             'space id: {}, '
                             'new recorder id: {}').format(
                                 e_r['recorder_id'],
                                 session.ExternalId,
                                 e['space']['id'],
                                 e_r['relocated_recorder_id']))

                    e_r['id'] = session.Id
                    e_r['folder']['name'] = session.FolderName
                    e_r['folder']['id'] = session.FolderId
                    e_r['is_broadcast'] = session.IsBroadcast
                    if 'is_public' in e_r:
                        e_r['is_public'] = session_access[session.Id].IsPublic

                    # actual recording start and duration
                    start_utc = session.StartTime.astimezone(pytz.utc)
                    end_utc = start_utc + \
                        datetime.timedelta(seconds=int(session.Duration))
                    e_r['start'] = start_utc.isoformat()
                    e_r['end'] = end_utc.isoformat()

                    if 'auth' in e_r['folder']:
                        e_r['folder']['auth'] = {
                            'creators': get_panopto_folder_creators(
                                session.FolderId)
                        }

    # fill in unscheduled event ids
    for e in event_sessions:
        e_r = e['recording']
        if (e['space']['id'] and not (
                'recorder_id' in e_r and e_r['recorder_id'])):
            space_id = e['space']['id']
            if not (space_id in recorders and recorders[space_id]):
                recorders[space_id] = get_recorder_id_for_space_id(space_id)

            if recorders[space_id]:
                e_r['recorder_id'] = recorders[space_id]

        e['key'] = schedule_key(
            e['contact']['uwnetid'], e_r['name'], e_r['external_id'],
            e_r['recorder_id'], e['event']['start'], e['event']['end'])


def get_recorder_id_for_space_id(space_id):
    try:
        return get_recorder_details(space_id)[0].Id
    except Exception as ex:
        logger.error("Cannot fetch recorder details for space {}: {}".format(
            space_id, ex))
        pass

    return None


def load_class_from_module_setting(
        module_name_setting, class_name, *args, **kwargs):
    module_name = getattr(settings, module_name_setting)
    if module_name is None:
        raise Exception("Missing setting: {}".format(module_name_setting))

    try:
        module = import_module(module_name)
        return getattr(module, class_name)(args, kwargs)
    except Exception as ex:
        raise Exception(
            "Cannot load module {}: {}".format(module_name, ex))
