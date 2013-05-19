from django.conf.urls import patterns, include, url
from django.conf import settings
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from django.contrib.auth.decorators import login_required
admin.autodiscover()
admin.site.login = login_required(admin.site.login)

urlpatterns = patterns('',
    url(r'^$', 'Observer.views.home'),
    url(r'^syncdb$', 'Observer.views.syncdb'),
    
    url(r'^history$', 'Observer.endpoints.history'),
    url(r'^retrieve$', 'Observer.endpoints.retrieve'),
    
    url(r'^' + settings.LOGIN_URL[1:] + '$', 'Observer.authorize.user_login'),
    url(r'^' + settings.LOGOUT_URL[1:] + '$', 'Observer.authorize.user_logout'),
    url(r'^renew$', 'Observer.authorize.user_renew'),
    
    url(r'^crawl$', 'Observer.backend.crawl'),
    url(r'^console/$', 'Observer.console.main'),

    url(r'^admin/', include(admin.site.urls)),
)
