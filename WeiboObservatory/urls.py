from django.conf.urls import patterns, include, url
from django.conf import settings

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'Observer.views.home'),
    url(r'^' + settings.LOGIN_URL[1:] + '$', 'Observer.authorize.user_login'),
    url(r'^logout$', 'Observer.authorize.user_logout'),
    url(r'^crawl$', 'Observer.backend.crawl'),
    # Examples:
    # url(r'^$', 'WeiboObservatory.views.home', name='home'),
    # url(r'^WeiboObservatory/', include('WeiboObservatory.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)
