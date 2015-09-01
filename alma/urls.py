from django.conf import settings
from django.conf.urls import include, patterns, url
from django.conf.urls.static import static
from django.contrib import admin

from .items import views as items
from .requests import views as requests
from .users import views as users

admin.autodiscover()

urlpatterns = patterns(
    '',
    # Examples:
    # url(r'^$', 'alma.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    # the django admin interface is always nice to have
    url(r'^admin/', include(admin.site.urls)),

    # the homepage goes straight to a template. But you may want to change this
    # into a normal view function
    url(r'^$', requests.main, name='home'),
    url(r'^login/?$', 'djangocas.views.login', name="login"),
    url(r'^logout/?$', 'djangocas.views.logout', name="logout"),

    url(r'^items/autocomplete/?$', items.autocomplete, name='items-autocomplete'),

    url(r'^requests/calendar/?$', requests.calendar, name='requests-calendar'),
    url(r'^requests/available/?$', requests.available, name='requests-available'),
    url(r'^requests/user/?$', requests.user, name='requests-user'),
    url(r'^requests/delete/(?P<request_id>.+)?$', requests.delete, name='requests-delete'),

    url(r'^users/autocomplete/?$', users.autocomplete, name='users-autocomplete'),

    # these url routes are useful for password reset functionality and logging in and out
    # https://github.com/django/django/blob/master/django/contrib/auth/urls.py
    # url(r'', include('django.contrib.auth.urls')),

    # these routes allow you to masquerade as a user, and login as them from the command line
    url(r'^cloak/', include('cloak.urls'))
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static("htmlcov", document_root="htmlcov", show_indexes=True)
