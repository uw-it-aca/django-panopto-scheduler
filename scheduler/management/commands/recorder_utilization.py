# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.core.management.base import BaseCommand
from uw_r25.reservations import get_reservations
from panopto_client.session import SessionManagement
from panopto_client.remote_recorder import RemoteRecorderManagement
import csv
import logging


# disable chatty libraries
logging.getLogger('suds').setLevel(logging.INFO)
logging.getLogger('urllib3').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Recorder utilzation CSV report."

    def add_arguments(self, parser):
        parser.add_argument('report_file', type=str, nargs=1)

    def handle(self, *args, **options):
        session_api = SessionManagement()
        recorder_api = RemoteRecorderManagement()

        recorders = {}

        logger.info("Collecting recorder list")

        for recorder in recorder_api.listRecorders():

            space_id = recorder.ExternalId

            if space_id:
                logger.info(f"Collect sessions for recorder {recorder.Name}")

                if space_id not in recorders:
                    recorders[space_id] = {
                        'id': recorder.Id,
                        'disconnected': (
                            recorder.State.lower() == 'disconnected'),
                        'name': recorder.Name,
                        'scheduled_courses': set(),
                        'nonscheduled_courses': set()
                    }

                if not recorder.ScheduledRecordings:
                    continue

                for session in session_api.getSessionsById(
                        recorder.ScheduledRecordings[0])[0]:
                    if session.ExternalId:
                        try:
                            # 2021-autumn-BIOC-440-A-2021-10-20
                            year, term, cur, course, section, yy, mm, dd = \
                                tuple(session.ExternalId.split('-'))
                        except ValueError:
                            continue

                        recorders[space_id]['scheduled_courses'].add(
                            f"{year}-{term}-{cur}-{course}-{section}")

                logger.info(
                    f"Collect reservations for space_id {space_id}")

                for reservation in get_reservations(space_id=str(space_id)):
                    try:
                        # ASTR 101 A ASTR101A 20251
                        cur, course, section, x, term = \
                            tuple(reservation.event_name.split(' '))
                        course_id = (f"{term[:4]}-{self.quarter(term[4:])}-"
                                     f"{cur}-{course}-{section}")
                        if course_id not in recorders[space_id][
                                'scheduled_courses']:
                            recorders[space_id]['nonscheduled_courses'].add(
                                course_id)
                    except (ValueError, KeyError):
                        continue

        logger.info(f"Writing report {options['report_file'][0]}")

        with open(options['report_file'][0], 'w') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow([
                "recorder", "recorder id", "space id", "connected",
                "scheduled", "non-scheduled", "utilization"])
            for space_id, recorder in recorders.items():
                scheduled = len(recorder['scheduled_courses'])
                unscheduled = len(recorder['nonscheduled_courses'])
                total = scheduled + unscheduled
                percentage = ((scheduled / total) * 100) if total else 0.0
                csvwriter.writerow([
                    recorder['name'], recorder['id'], space_id,
                    not recorder['disconnected'], scheduled, unscheduled,
                    percentage])

    def quarter(self, term_index):
        return {
            '1': 'winter',
            '2': 'spring',
            '3': 'summer',
            '4': 'autumn'}[term_index]
