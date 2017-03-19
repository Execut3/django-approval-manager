from django.conf.urls import patterns, url
from views import *

urlpatterns = patterns('',
                       url(r'^manage$', manage_approvals,
                           name='manage_approves'),
                       url(r'^action/(?P<approve_id>\d+)/$',
                           action_on_approvals,
                           name='approve'),
                       )
