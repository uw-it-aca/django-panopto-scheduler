from django.conf import settings
from django.conf.urls import include, url
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from scheduler.views import home, courses, events, recorders
from scheduler.views.course import CourseScheduleView
from scheduler.views.api.schedule import Schedule
from scheduler.views.api.recorder import Recorder
from scheduler.views.api.space import Space
from scheduler.views.api.session import (
    Session, SessionPublic, SessionBroadcast, SessionRecordingTime)
from scheduler.views.api.folder import Folder


urlpatterns = [
    url(r'^$', RedirectView.as_view(url='courses/', permanent=True)),
    url(r'^recorders/?$', recorders, name='recorders-view'),
    url(r'^course/?$', CourseScheduleView.as_view()),
    url(r'^courses/?$', courses, name='courses-view'),
    url(r'^events/?$', events, name='events-view'),
    url(r'^(blti/)?api/v1/recorder/(?P<recorder_id>[0-9a-f\-]+)?$',
        Recorder().run),
    url(r'^(blti/)?api/v1/space/(?P<space_id>[0-9]+)?$', Space().run),
    url(r'^(blti/)?api/v1/session/(?P<session_id>[0-9a-f\-]+)/public/?$',
        SessionPublic().run),
    url(r'^(blti/)?api/v1/session/(?P<session_id>[0-9a-f\-]+)/broadcast/?$',
        SessionBroadcast().run),
    url(r'^(blti/)?api/v1/session/(?P<session_id>'
        r'[0-9a-f\-]+)/recordingtime/?$',
        SessionRecordingTime().run),
    url(r'^(blti/)?api/v1/session/(?P<session_id>[0-9a-f\-]+)?$',
        Session().run),
    url(r'^(blti/)?api/v1/schedule/(?P<course_id>[\d\w& \a-zA-Z0-9]+)?$',
        Schedule().run),
    url(r'^(blti/)?api/v1/folder/(?P<folder_id>[0-9a-f\-]+)?$',
        Folder().run)
]

# debug routes for developing error pages
if settings.DEBUG:
    urlpatterns += [
        url(r'^404$', TemplateView.as_view(template_name='404.html')),
        url(r'^500$', TemplateView.as_view(template_name='500.html')),
    ]
