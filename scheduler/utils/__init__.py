from django.conf import settings
from restclients.pws import PWS
from restclients.sws.section import get_section_by_label, get_section_by_url
from restclients.sws.term import get_current_term, get_next_term
from restclients.exceptions import InvalidNetID, DataFailureException
from scheduler.models import Course, Curriculum
from scheduler.exceptions import InvalidUser
from scheduler.utils.validation import Validation
from restclients.r25.events import get_event_by_alien_id
from restclients.r25.reservations import get_reservations
from restclients.canvas.courses import Courses as CanvasCourses
from scheduler.utils.recorder import get_recorder_details, RecorderException
from scheduler.utils.session import get_sessions_by_external_ids
from scheduler.utils.session import get_sessions_by_session_ids
from panopto_client.access import AccessManagement
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


def netid_from_email(email):
                raise InvalidUser()


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
                except:
                    continue

            if len(joint_course_ids):
                joint_course_ids.sort()
                course = valid.course_id(joint_course_ids[0])

    contact = course_event_title_and_contact(course)
    folder = panopto_course_folder(course, contact['title_long'])
    for r in event.reservations:

        event_session = event_session_from_reservation(r)

        event_session['joint'] = joint if len(joint) else None

        event_session['recording']['folder'] = folder

        name, external_id = panopto_course_session(course, r.start_datetime)
        event_session['recording']['name'] = name
        event_session['recording']['external_id'] = external_id

        recorders[r.space_reservation.space_id] = None
        session_external_ids.append(external_id)

        event_session['schedulable'] = True if folder['external_id'] else False

        event_session['contact'] = contact

        event_sessions.append(event_session)

    mash_in_panopto_sessions(event_sessions, session_external_ids, recorders)

    return event_sessions


def space_events_and_recordings(params):
    search = {
        'space_id': params.get('space_id'),
        'start_dt': params.get('start_dt'),
        'session_ids': params.get('session_ids'),
        'recorder_id': params.get('recorder_id'),
    }

    current_term = get_current_term()
    next_term = get_next_term()

    event_sessions = []
    event_external_ids = []
    recorders = {
        search['space_id']: search['recorder_id'],
    }

    if search['recorder_id'] and search['session_ids']:
        sessions = get_sessions_by_session_ids(
            search['session_ids'].split(','))

        for s in sessions:
            event_session = event_session_from_scheduled_recording(
                s, recorders)
            r = s.RemoteRecorderIds.guid[0] \
                if hasattr(s.RemoteRecorderIds, 'guid') else None
            if s.ExternalId not in event_external_ids:
                event_sessions.append(event_session)
                event_external_ids.append(s.ExternalId)
            elif r == search['recorder_id']:
                for i, e in enumerate(event_sessions):
                    if e['recording']['external_id'] == s.ExternalId:
                        event_sessions[i] = event_session

        return event_sessions

    if search['space_id'] and search['start_dt']:
        start_dt = parser.parse(search['start_dt']).date()

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
        for event_session in event_sessions:

            # generate external_id
            if event_session['profile'].lower() in UW_MEETING_TYPES:
                name = event_session['name'][0] if isinstance(
                    event_session['name'], list) else event_session['name']
                match = re.match(r'^([\w& ]+) (\d{3}) ([A-Z][A-Z0-9]?)$', name)
                if match:
                    term = None
                    if start_dt > current_term.first_day_quarter \
                       and start_dt < current_term.last_day_instruction:
                        term = current_term
                    elif start_dt > next_term.first_day_quarter \
                            and start_dt < next_term.last_day_instruction:
                        term = next_term

                    if term:
                        course = Course(year=str(term.year),
                                        quarter=term.quarter,
                                        curriculum=match.group(1).upper(),
                                        number=match.group(2),
                                        section=match.group(3).upper())

                        contact = course_event_title_and_contact(course)
                        folder = panopto_course_folder(course,
                                                       contact['title_long'])

                        event_session['recording']['folder'] = folder
                        event_session['contact'] = contact

                        name, eid = panopto_course_session(
                            course, search['start_dt'])
                        event_session['recording']['name'] = name
                        event_session['recording']['external_id'] = eid
                        event_external_ids.append(eid)
            else:
                set_panopto_generic_folder(event_session)
                set_panopto_generic_session(event_session)
                event_external_ids.append(event_session['recording']['external_id'])

    mash_in_panopto_sessions(event_sessions, event_external_ids, recorders)

    return event_sessions


def event_session_from_reservation(r):
    session = {
        'profile': r.profile_name if hasattr(r, 'profile_name') else '',
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
        session['space']['id'] = r.space_reservation.space_id
        session['space']['name'] = r.space_reservation.name
        session['space']['formal_name'] = r.space_reservation.formal_name

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


def event_session_from_scheduled_recording(s, recorders):
    space_id, recorder_id = recorders.items()[0]

    start_utc = s.StartTime.astimezone(pytz.utc)
    end_utc = start_utc + datetime.timedelta(seconds=int(s.Duration))

    session = {
        'profile': '',
        'name': s.Name,
        'schedulable': True,
        'space': {
            'id': space_id,
            'name': None,
            'formal_name': None
        },
        'recording': {
            'name': s.Name,
            'id': s.Id if s.RemoteRecorderIds.guid[0] == recorder_id else None,
            'external_id': s.ExternalId,
            'recorder_id': recorder_id,
            'start': start_utc.isoformat(),
            'end': end_utc.isoformat(),
            'folder': {
                'name': s.FolderName,
                'id': s.FolderId,
                'external_id': s.FolderId,
            },
            'is_broadcast': s.IsBroadcast,
            'is_public': False,
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
        session['recording']['folder']['external_id'])

    return session


def mash_in_panopto_sessions(event_sessions, session_external_ids, recorders):
    # mash in panopto recorder schedule
    access = {}
    # Enable when service manager requests feature
    # api = AccessManagement()
    if len(session_external_ids):
        sessions = get_sessions_by_external_ids(session_external_ids)
        for session in sessions if sessions else []:
            for e in event_sessions:
                # Enable when service manager requests feature
                # if session.Id not in access:
                # access[session.Id] = api.getSessionAccessDetails(session.Id)

                e_r = e['recording']
                if session.ExternalId == e_r['external_id']:
                    e_r['recorder_id'] = session.RemoteRecorderIds.guid[0] \
                        if hasattr(session.RemoteRecorderIds, 'guid') else None
                    recorders[e['space']['id']] = e_r['recorder_id']
                    e_r['id'] = session.Id
                    e_r['folder']['id'] = session.FolderId
                    e_r['is_broadcast'] = session.IsBroadcast
                    # Enable when service manager requests feature
                    # e_r['is_public'] = access[session.Id].IsPublic
                    e_r['is_public'] = False

                    # actual recording start and duration
                    start_utc = session.StartTime.astimezone(pytz.utc)
                    end_utc = start_utc + \
                        datetime.timedelta(seconds=int(session.Duration))
                    e_r['start'] = start_utc.isoformat()
                    e_r['end'] = end_utc.isoformat()

    # fill in unscheduled event ids
    for e in event_sessions:
        e_r = e['recording']
        if not ('recorder_id' in e_r and e_r['recorder_id']):
            space_id = e['space']['id']
            if not (space_id in recorders and recorders[space_id]):
                try:
                    recorders[space_id] = get_recorder_details(space_id)[0].Id
                except:
                    recorders[space_id] = None
                    pass

            if recorders[space_id]:
                e_r['recorder_id'] = recorders[space_id]

        e['key'] = course_event_key(e['contact']['uwnetid'],
                                    e_r['name'],
                                    e_r['external_id'],
                                    e_r['recorder_id'],
                                    e_r['folder']['external_id'])


def set_panopto_generic_folder(event):
    id_string = "%s - %s" % (event['name'], event['space']['id'])
    event['recording']['folder']['name'] = event['name']
    event['recording']['folder']['external_id'] = panopto_generic_external_id(id_string)


def set_panopto_generic_session(event):
    name = "%s - %s" % (event['name'],
                        parser.parse(event['event']['start']).strftime('%Y-%m-%d'))
    id_string = "%s - %s" % (name, event['space']['id'])
    event['recording']['name'] = name
    event['recording']['external_id'] = panopto_generic_external_id(id_string)


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
    start_dt = parser.parse(start_datetime)
    start_date = start_dt.strftime('%Y-%m-%d')

    name = "%s %s %s - %s" % (course.curriculum, course.number,
                              course.section, start_date)
    external_id = panopto_course_external_id(course, start_date)
    return (name, external_id)


# session_external_id: 2014-autumn-BIOL-404-A-2014-10-27
def panopto_course_external_id(course, start_datetime):
    start_dt = parser.parse(start_datetime)
    start_date = start_dt.strftime('%Y-%m-%d')

    return "%s-%s-%s-%s-%s-%s" % (course.year, course.quarter,
                                  course.curriculum, course.number,
                                  course.section, start_date)


def panopto_course_folder(course, title):
    folder = "%s%s %s - %s %s %s: %s" % (course.quarter[0:1].upper(),
                                         course.quarter[1:], course.year,
                                         course.curriculum, course.number,
                                         course.section, title.title())

    # folder id needs to match canvas course id
    id = canvas_course_id(course)

    try:
        external_id = str(CanvasCourses().get_course_by_sis_id(id).course_id)
    except Exception as ex:
        logger.exception(ex)
        external_id = None

    return {
        'name': folder,
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
        'email': email if email and len(email) else "%s@uw.edu" % uwnetid if uwnetid else ''
    }

def course_event_key(netid, name, external_id,
                     recorder_id, folder_external_id):
    to_sign = '%s,%s,%s,%s,%s(%s)' % (netid,
                                      name,
                                      external_id,
                                      recorder_id,
                                      folder_external_id,
                                      getattr(settings,
                                              'PANOPTO_API_TOKEN',
                                              ''))

    return sha1(to_sign).hexdigest().upper()


def get_sws_section(course):
    return get_section_by_label(sws_course_id(course),
                                include_instructor_not_on_time_schedule=False)


def sws_course_id(course):
    return "%s,%s,%s,%s/%s" % (course.year, course.quarter,
                               course.curriculum, course.number,
                               course.section)
