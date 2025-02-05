"""chats URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import re

from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, re_path
from django.views.static import serve

from chats.apps.api.v1.swagger import schema_view

urlpatterns = [
    path("", lambda _: HttpResponse()),
    path("doc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    path("admin/", admin.site.urls),
    path("v1/", include("chats.apps.api.v1.urls")),
    path("", include("django_prometheus.urls")),
]

# Static files

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

else:
    regex_path = "^{}(?P<path>.*)$".format(re.escape(settings.STATIC_URL.lstrip("/")))
    urlpatterns.append(
        re_path(regex_path, serve, {"document_root": settings.STATIC_ROOT})
    )

if hasattr(settings, "MEDIA_URL"):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
