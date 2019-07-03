from django.conf import settings
from uw_pws import PWS
from uw_sws.section import get_section_by_label, get_section_by_url
from restclients_core.exceptions import InvalidNetID, DataFailureException
from scheduler.models import Curriculum
from scheduler.exceptions import InvalidUser
from scheduler.utils.validation import Validation
from uw_r25.events import get_event_by_alien_id
from uw_r25.reservations import get_reservations
from uw_canvas.courses import Courses as CanvasCourses
from scheduler.utils.recorder import get_recorder_details
from scheduler.utils.session import get_sessions_by_external_ids
from scheduler.utils.session import get_sessions_by_session_ids
from panopto_client.access import AccessManagement
from panopto_client.user import UserManagement
from panopto_client.session import SessionManagement
from panopto_client import PanoptoAPIException
from dateutil import parser, tz
from nameparser import HumanName
from hashlib import sha1
import datetime
import pytz
import logging
import re


class CourseEventException(Exception):
    pass


logger = logging.getLogger(__name__)
UW_CAMPUS = ['seattle', 'bothell', 'tacoma']
UW_DOMAIN = ['uw.edu', 'washington.edu', 'u.washington.edu']
UW_MEETING_TYPES = ['lecture', 'seminar', 'quiz', 'lab', 'final']


def person_from_username(username):
    try:
        return PWS().get_person_by_netid(username.lower())
    except InvalidNetID as ex:
        raise InvalidUser()
    except DataFailureException as ex:
        if ex.status == 404:
            raise InvalidUser()
        else:
            raise


def course_location_and_recordings(course):
    try:
        event = get_event_by_alien_id(r25_alien_uid(course))

        if not event:
            raise CourseEventException("No Course Events Found")

        return course_recording_sessions(course, event)
    except PanoptoAPIException as err:
        raise CourseEventException(
            "There was a problem connecting to the Panopto server. %s" % err)
    except Exception as ex:
        logger.exception(ex)
        raise CourseEventException("Data Failure: %s" % ex)


def course_recording_sessions(course, event):
    event_sessions = []
    recorders = {}
    session_external_ids = []
    joint = []
    valid = Validation()

    # cross listed?
    if len(event.binding_reservations):
        # default to Canvas course that student sections are provisioned
        section = get_sws_section(course)
        if not section.is_withdrawn and len(section.joint_section_urls):
            joint_course_ids = [canvas_course_id(course)]
            for url in section.joint_section_urls:
                try:
                    joint_section = get_section_by_url(url)
                    if not joint_section.is_withdrawn:
                        joint_course_id = joint_section.canvas_course_sis_id()
                        joint_course_ids.append(joint_course_id)
                        c = valid.course_id(joint_course_id)
                        joint.append("%s %s %s" %
                                     (c.curriculum, c.number, c.section))
                except Exception:
                    continue

            if len(joint_course_ids):
                joint_course_ids.sort()
                course = valid.course_id(joint_course_ids[0])

    contact = course_event_title_and_contact(course)
    folder = panopto_course_folder(course, contact['title_long'])
    for rsv in event.reservations:

        event_session = event_session_from_reservation(rsv)

        if event_session['profile'].split()[-1].lower() in ['lab', 'final']:
            continue

        event_session['joint'] = joint if len(joint) else None

        event_session['recording']['folder'] = folder

        name, external_id = panopto_course_session(course, rsv.start_datetime)
        event_session['recording']['name'] = name
        event_session['recording']['external_id'] = external_id

        if rsv.space_reservation and rsv.space_reservation.space_id:
            recorders[rsv.space_reservation.space_id] = None

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
        sessions = get_sessions_by_session_ids(
            search['session_ids'].split(','))

        for s in sessions:
            event_session = event_session_from_scheduled_recording(s)
            event_sessions.append(event_session)

        return event_sessions

    if search['space_id'] and search['start_dt']:
        reservations = get_reservations(**search)

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

    match = re.match(r'^([a-z][0-9a-z]{0,7})@(%s)$' % ('|'.join(UW_DOMAIN)),
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

    session['key'] = course_event_key(
        session['contact']['uwnetid'],
        session['recording']['name'],
        session['recording']['external_id'],
        session['recording']['recorder_id'],
        session['event']['start'],
        session['event']['end'])

    return session


def mash_in_panopto_sessions(event_sessions, session_external_ids, recorders):
    # mash in panopto recorder schedule
    session_access = {}
    access_api = AccessManagement()
    if len(session_external_ids):
        sessions = get_sessions_by_external_ids(session_external_ids)
        for session in sessions if sessions else []:
            for e in event_sessions:
                e_r = e['recording']

                # only do the work of getting details if they're requested
                if 'is_public' in e_r and session.Id not in session_access:
                    details = access_api.getSessionAccessDetails(session.Id)
                    session_access[session.Id] = details

                if session.ExternalId == e_r['external_id']:
                    start_time = parser.parse(e_r['start'])
                    end_time = parser.parse(e_r['end'])
                    if not (start_time <= session.StartTime and
                            end_time >= session.StartTime):
                        continue

                    e_r['recorder_id'] = session.RemoteRecorderIds.guid[0] if (
                        hasattr(session.RemoteRecorderIds, 'guid')) else None

                    if e['space']['id']:
                        recorders[e['space']['id']] = e_r['recorder_id']

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
                try:
                    recorders[space_id] = get_recorder_details(space_id)[0].Id
                except Exception:
                    recorders[space_id] = None
                    pass

            if recorders[space_id]:
                e_r['recorder_id'] = recorders[space_id]

        e['key'] = course_event_key(e['contact']['uwnetid'],
                                    e_r['name'],
                                    e_r['external_id'],
                                    e_r['recorder_id'],
                                    e['event']['start'],
                                    e['event']['end'])


def get_panopto_folder_creators(folder_id):
    user_api = UserManagement()
    access_api = AccessManagement()
    creators = []
    folder_access = access_api.getFolderAccessDetails(folder_id)

    if ('UsersWithCreatorAccess' in folder_access and
            folder_access['UsersWithCreatorAccess'] and
            len(folder_access['UsersWithCreatorAccess'])):
        guids = folder_access['UsersWithCreatorAccess'][0]
        if len(guids):
            users = user_api.getUsers(guids)
            for user in users[0]:
                match = re.match(
                    r'^%s\\(.+)$' % (
                        settings.PANOPTO_API_APP_ID), user['UserKey'])
                if match:
                    creators.append(
                        match.group(1) if match else user['UserKey'])

    return creators


def set_panopto_generic_folder(event):
    session_api = SessionManagement()
    id_string = "%s - %s" % (event['name'], event['space']['id'])
    folder_name = event['name']
    folder_external_id = panopto_generic_external_id(id_string)
    creators = []

    folders = session_api.getFoldersList(search_query=event['name'])
    if folders and len(folders) == 1:
        folder_name = folders[0].Name
        folder_external_id = folders[0].ExternalId
        creators = get_panopto_folder_creators(folders[0].Id)

    event['recording']['folder']['name'] = folder_name
    event['recording']['folder']['external_id'] = folder_external_id
    event['recording']['folder']['auth'] = {'creators': creators}


def set_panopto_generic_session(event):
    name = "%s - %s" % (
        event['name'],
        _local_ymd_from_utc_date_string(event['event']['start']))
    id_string = "%s - %s" % (name, event['space']['id'])
    event['recording']['name'] = name
    event['recording']['external_id'] = panopto_generic_external_id(id_string)
    event['recording']['is_public'] = False


def _local_ymd_from_utc_date_string(utc_date_string):
    from_zone = tz.tzutc()
    to_zone = pytz.timezone("America/Los_Angeles")
    dt_utc = parser.parse(utc_date_string).replace(tzinfo=from_zone)
    dt_local = dt_utc.astimezone(to_zone)
    return dt_local.strftime('%Y-%m-%d')


def panopto_generic_external_id(id_string):
    return sha1(id_string).hexdigest().upper()


def r25_alien_uid(course):
    # r25 alien_id: 2014-4 0-MATH 124 A
    return "%s-%s %s-%s %s %s" % (course.year,
                                  quarter_ordinal(course.quarter),
                                  campus_ordinal(course),
                                  course.curriculum,
                                  course.number,
                                  course.section)


def campus_ordinal(course):
    try:
        return Curriculum.objects.get(
            curriculum_abbr=course.curriculum).campus_code
    except Curriculum.DoesNotExist:
        section = get_sws_section(course)
        course_campus = section.course_campus
        campus_code = UW_CAMPUS.index(course_campus.lower())
        curriculum = Curriculum(curriculum_abbr=course.curriculum,
                                campus_code=campus_code)
        curriculum.save()
        return campus_code


def panopto_course_session(course, start_datetime):
    name = "%s %s %s - %s" % (course.curriculum, course.number,
                              course.section,
                              _local_ymd_from_utc_date_string(start_datetime))
    external_id = panopto_course_external_id(
        course, _local_ymd_from_utc_date_string(start_datetime))
    return (name, external_id)


# session_external_id: 2014-autumn-BIOL-404-A-2014-10-27
def panopto_course_external_id(course, start_datetime):
    start_dt = parser.parse(start_datetime)
    start_date = start_dt.strftime('%Y-%m-%d')

    return "%s-%s-%s-%s-%s-%s" % (course.year, course.quarter,
                                  course.curriculum, course.number,
                                  course.section, start_date)


def panopto_course_folder(course, title):
    quarter_initial = course.quarter[0:1].upper()
    quarter_lower = course.quarter[1:]
    folder_prefix = "%s%s %s - " % (
        quarter_initial, quarter_lower, course.year)

    # folder id needs to match canvas course id
    id = canvas_course_id(course)

    try:
        canvas_course = CanvasCourses().get_course_by_sis_id(id)
        external_id = str(canvas_course.course_id)
        folder = canvas_course.name
    except Exception as ex:
        logger.exception(ex)
        external_id = None
        folder = "%s %s %s %s%s %s: %s" % (
            course.curriculum, course.number, course.section, quarter_initial,
            quarter_lower[:1], str(course.year)[2:], title.title())

    return {
        'name': "%s%s" % (folder_prefix, folder),
        'external_id': external_id
    }


def canvas_course_id(course):
    return "%s" % '-'.join([course.year,
                            course.quarter,
                            course.curriculum,
                            course.number,
                            course.section])


def quarter_ordinal(quarter):
    quarters = ['winter', 'spring', 'summer', 'autumn']
    return quarters.index(quarter.lower()) + 1


def course_event_title_and_contact(course):
    try:
        section = get_sws_section(course)
        meeting = section.meetings[0] if hasattr(
            section, 'meetings') and len(section.meetings) else None
        instructor = meeting.instructors[0] if hasattr(
            meeting, 'instructors') and len(meeting.instructors) else None
        first_name = instructor.first_name if hasattr(
            instructor, 'first_name') else ''
        surname = instructor.surname if hasattr(instructor, 'surname') else ''
        uwnetid = instructor.uwnetid if hasattr(instructor, 'uwnetid') else ''
        email = instructor.email1 if hasattr(instructor, 'email1') else ''
        name = HumanName(' '.join([first_name, surname]))
        name.capitalize()
    except DataFailureException as err:
        if err.status == 404:
            section = None
            name = None
            email = None
            uwnetid = None
        else:
            raise

    return {
        'title_long': section.course_title_long if section else '',
        'name': '%s %s' % (name.first, name.last) if name else '',
        'uwnetid': uwnetid if uwnetid else '',
        'email': email if (
            email and len(email)) else "{}@uw.edu".format(
                uwnetid if uwnetid else '')
    }


def course_event_key(netid, name, external_id, recorder_id, start, end):
    to_sign = '{},{},{},{},{},{},({})'.format(
        netid if netid else '',
        name,
        external_id,
        recorder_id,
        start,
        end,
        getattr(settings, 'PANOPTO_API_TOKEN', ''))

    return sha1(to_sign).hexdigest().upper()


def get_sws_section(course):
    return get_section_by_label(sws_course_id(course),
                                include_instructor_not_on_time_schedule=False)


def sws_course_id(course):
    return "%s,%s,%s,%s/%s" % (course.year, course.quarter,
                               course.curriculum, course.number,
                               course.section)
