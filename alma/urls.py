from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.conf import settings
from django.views.generic import TemplateView
from .users import views as users
from .requests import views as requests

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
    url(r'^$', requests.calendar, name='home'),
    url(r'^login/?$', 'djangocas.views.login', name="login"),
    url(r'^logout/?$', 'djangocas.views.logout', name="logout"),

    # Here we define all the URL routes for the users app. Technically, you
    # could put these routes in the app itself, but for non-reusable apps, we
    # keep them in the main urlconfs file
    url(r'^users/home/?$', users.home, name='users-home'),
    url(r'^users/detail/(?P<user_id>\d+)?$', users.detail, name='users-detail'),
    url(r'^users/list/?$', users.list_, name='users-list'),
    url(r'^users/create/?$', users.create, name='users-create'),
    url(r'^users/edit/(?P<user_id>\d+)/?$', users.edit, name='users-edit'),
    url(r'^users/delete/(?P<user_id>\d+)/?$', users.delete, name='users-delete'),

    # these url routes are useful for password reset functionality and logging in and out
    # https://github.com/django/django/blob/master/django/contrib/auth/urls.py
    #url(r'', include('django.contrib.auth.urls')),

    # these routes allow you to masquerade as a user, and login as them from the command line
    url(r'^cloak/', include('cloak.urls'))
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static("htmlcov", document_root="htmlcov", show_indexes=True)
