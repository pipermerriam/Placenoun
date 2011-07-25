from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:

    (r'^$', 'placenoun.pn.views.index'),
    (r'^_/(?P<id>[0-9]+)/$', 'placenoun.pn.views.get_by_id'),
    (r'^random/$', 'placenoun.pn.views.random_noun'),
    (r'^random/debug/$', 'placenoun.pn.views.random_noun', {'debug': True}),
    (r'^random/(?P<width>[0-9]+)/(?P<height>[0-9]+)/debug/$', 'placenoun.pn.views.random_noun', {'debug': True}),
    (r'^random/(?P<width>[0-9]+)/(?P<height>[0-9]+)/$', 'placenoun.pn.views.random_noun'),
    (r'^(?P<noun>[a-zA-Z+]+)/debug/$', 'placenoun.pn.views.noun', {'debug': True}),
    (r'^(?P<noun>[a-zA-Z+]+)/$', 'placenoun.pn.views.noun'),
    (r'^(?P<noun>[a-zA-Z+]+)/(?P<width>[0-9]+)/(?P<height>[0-9]+)/debug/$', 'placenoun.pn.views.noun_static', {'debug': True}),
    (r'^(?P<noun>[a-zA-Z+]+)/(?P<width>[0-9]+)/(?P<height>[0-9]+)/$', 'placenoun.pn.views.noun_static'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)
