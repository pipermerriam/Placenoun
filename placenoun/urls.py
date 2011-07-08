from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:

    (r'^_/(?P<id>[0-9]+)/$', 'placenoun.pn.views.get_by_id'),
    (r'^(?P<noun>[a-zA-Z+]+)/$', 'placenoun.pn.views.noun'),
    (r'^(?P<noun>[a-zA-Z+]+)/(?P<width>[0-9]+)/(?P<height>[0-9]+)/$', 'placenoun.pn.views.noun_static'),
    # url(r'^$', 'placenoun.views.home', name='home'),
    # url(r'^placenoun/', include('placenoun.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)
