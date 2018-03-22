from django.core.management.base import BaseCommand
from optparse import make_option
from uw_sws.section import get_section_by_label
from panopto_client.session import SessionManagement
from panopto_client.remote_recorder import RemoteRecorderManagement
from dateutil import parser, tz
import datetime
import re
import sys


class Command(BaseCommand):
    help = "Matchrecording session dates to SWS meeting times"

    option_list = BaseCommand.option_list + (
        make_option('--commit', dest='commit', action="store_true",
                    default=False,
                    help='Update Panopto recording with SWS meeting time'),
        make_option('--stdin', dest='stdin', action="store_true",
                    default=False,
                    help='get Panopto session external ids on standard input'),
    )

    def handle(self, *args, **options):
        self._commit = options['commit']
        self._courses = {}
        self._session = SessionManagement()
        self._recorder = RemoteRecorderManagement()

        if options['stdin']:
            for line in sys.stdin:
                self._process_course(line.rstrip('\n'))
        else:
            for session in args:
                self._process_course(session)

    def _process_course(self, session_id):
        # 2015-spring-PSYCH-202-A-2015-06-04
        course = re.match(r'^(20[0-9]{2})-(winter|spring|summer|autumn)'
                          r'-([A-Z ]+)-([0-9]{3})-([A-Z][A-Z0-9]*)-2*',
                          session_id)

        if course:
            label = "%s,%s,%s,%s/%s" % (
                course.group(1), course.group(2), course.group(3),
                course.group(4), course.group(5))

            if label not in self._courses:
                now = datetime.datetime.now(
                    tz.tzlocal()).replace(second=0, microsecond=0)
                section = get_section_by_label(
                    label, include_instructor_not_on_time_schedule=False)
                (start, end) = self._lecture_times(section)
                self._courses[label] = {
                    'start': start.split(':'),
                    'end': end.split(':')
                }

            offered = self._courses[label]
        else:
            print >> sys.stderr, "unrecognized session id: %s" % session_id
            return

        pan_session = self._session.getSessionsByExternalId([session_id])
        if 'Session' in pan_session and len(pan_session.Session) == 1:
            # broken-ass suds.
            fsuds = re.match(r'.*\<a\:StartTime\>([^<]+)\<\/a\:StartTime\>.*',
                             self._session._api.last_received().plain())
            if not fsuds:
                Exception('Untrustable time')

            pan_start = parser.parse(fsuds.group(1))
            pan_start_local = pan_start.astimezone(tz.tzlocal())
            sws_start_local = pan_start_local.replace(
                hour=int(offered['start'][0]),
                minute=int(offered['start'][1]))
            sws_end_local = pan_start_local.replace(
                hour=int(offered['end'][0]),
                minute=int(offered['end'][1]))

            schedule_delta = sws_start_local - pan_start_local

            duration_delta = (sws_end_local - sws_start_local).seconds - int(
                pan_session.Session[0].Duration)

            if schedule_delta or duration_delta:
                pan_start = (pan_start_local +
                             schedule_delta).astimezone(tz.tzutc())

                duration = pan_session.Session[0].Duration
                if duration_delta:
                    duration += duration_delta

                pan_end = pan_start + datetime.timedelta(0, duration)

                adjustment = [session_id, '(%s)' % pan_session.Session[0].Id,
                              '' if self._commit else 'WOULD', 'RESCHEDULE',
                              fsuds.group(1), 'TO',
                              pan_start.isoformat(), ':']

                if schedule_delta.days < 0:
                    adjustment.append("(-%s shift)" % (datetime.timedelta() -
                                                       schedule_delta))
                else:
                    adjustment.append("(%s shift)" % schedule_delta)

                if duration_delta:
                    adjustment.append('AND DURATION')
                    adjustment.append("%s" % duration_delta)
                    adjustment.append('seconds')

                print >> sys.stderr, ' '.join(adjustment)

                if self._commit:
                    result = self._recorder.updateRecordingTime(
                        pan_session.Session[0].Id,
                        pan_start.isoformat(),
                        pan_end.isoformat())
                    if not result:
                        print >> sys.stderr, "FAIL: null return value"
                    elif result.ConflictsExist:
                        print >> sys.stderr, "CONFLICT: %s" % (
                            result.ConflictingSessions[0][0].SessionName)
                    else:
                        print >> sys.stderr, "UPDATED %s" % (
                            result.SessionIDs[0][0])
            else:
                print >> sys.stderr, "%s: UNCHANGED" % (session_id)

        else:
            print >> sys.stderr, "unrecognized session id: %s" % session_id

    def _lecture_times(self, section):
        for meeting in section.meetings:
            if (meeting.meeting_type in ['lecture', 'quiz', 'seminar'] and
                    meeting.start_time and meeting.end_time):
                return meeting.start_time, meeting.end_time

        Exception("no lecture times set")
