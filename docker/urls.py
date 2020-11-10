from .base_urls import *
from django.conf.urls import include, re_path
from django.views.i18n import JavaScriptCatalog


urlpatterns += [
    re_path(r'^', include('scheduler.urls')),
    re_path(r'^restclients/', include('rc_django.urls')),
    re_path(r'^jsi18n/$', JavaScriptCatalog.as_view(packages=['scheduler']),
            name='javascript-catalog'),
]
