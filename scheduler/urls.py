# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.urls import re_path
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from scheduler.views import courses, events, recorders
from scheduler.views.course import CourseScheduleView
from scheduler.views.api.schedule import Schedule
from scheduler.views.api.recorder import Recorder
from scheduler.views.api.space import Space
from scheduler.views.api.user import UserValidation
from scheduler.views.api.session import (
    Session, SessionPublic, SessionBroadcast, SessionRecordingTime)
from scheduler.views.api.folder import Folder


urlpatterns = [
    re_path(r'^$', RedirectView.as_view(url='courses/', permanent=True)),
    re_path(r'recorders/?$', recorders, name='recorders-view'),
    re_path(r'courses/?$', courses, name='courses-view'),
    re_path(r'events/?$', events, name='events-view'),
    re_path(r'scheduler/course/?$', CourseScheduleView.as_view(),
            name='lti-launch'),
    re_path(r'scheduler/(blti/)?api/v1/'
            r'users/validate/?$', UserValidation.as_view(),
            name='api_user_validate'),
    re_path(r'scheduler/(blti/)?api/v1/'
            r'recorder/(?P<recorder_id>[0-9a-f\-]+)?$',
            Recorder.as_view(), name='api_recorder'),
    re_path(r'scheduler/(blti/)?api/v1/'
            r'space/(?P<space_id>[0-9]+)?$',
            Space.as_view(), name='api_space'),
    re_path(r'scheduler/(blti/)?api/v1/'
            r'session/(?P<session_id>[0-9a-f\-]+)/public/?$',
            SessionPublic.as_view(), name='api_session_public'),
    re_path(r'scheduler/(blti/)?api/v1/'
            r'session/(?P<session_id>[0-9a-f\-]+)/broadcast/?$',
            SessionBroadcast.as_view(), name='api_session_broadcast'),
    re_path(r'scheduler/(blti/)?api/v1/'
            r'session/(?P<session_id>[0-9a-f\-]+)/recordingtime/?$',
            SessionRecordingTime.as_view(), name='api_session_recording_time'),
    re_path(r'scheduler/(blti/)?api/v1/'
            r'session/(?P<session_id>[0-9a-f\-]+)?$',
            Session.as_view(), name='api_session'),
    re_path(r'scheduler/(blti/)?api/v1/'
            r'schedule/(?P<course_id>[\d\w& \a-zA-Z0-9\-]+)?$',
            Schedule.as_view()),
    re_path(r'scheduler/(blti/)?api/v1/'
            r'folder/(?P<folder_id>[0-9a-f\-]+)?$',
            Folder.as_view(), name='api_folder')
]

# debug routes for developing error pages
if settings.DEBUG:
    urlpatterns += [
        re_path(r'^404$', TemplateView.as_view(template_name='404.html')),
        re_path(r'^500$', TemplateView.as_view(template_name='500.html')),
    ]
