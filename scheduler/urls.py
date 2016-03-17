from django.conf import settings
from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView
from scheduler.views.api.schedule import Schedule
from scheduler.views.api.recorder import Recorder
from scheduler.views.api.space import Space
from scheduler.views.api.session import Session, SessionPublic, \
    SessionBroadcast, SessionRecordingTime
from scheduler.views.api.folder import Folder


urlpatterns = patterns(
    '',
    url(r'^/?$', 'scheduler.views.home.home'),
    url(r'^recorders/?$', 'scheduler.views.recorders.recorders'),
    url(r'^course/?$', 'scheduler.views.course.CourseSchedule'),
    url(r'^courses/?$', 'scheduler.views.courses.courses'),
    url(r'^events/?$', 'scheduler.views.events.events'),
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
)

# debug routes for developing error pages
if settings.DEBUG:
    urlpatterns += patterns(
        '',
        (r'^404$', TemplateView.as_view(template_name='404.html')),
        (r'^500$', TemplateView.as_view(template_name='500.html')),
    )
