from django.conf.urls import include, url
from django.contrib import admin

from genesim.apps.datasets import urls as datasets_urls

admin.autodiscover()

urlpatterns = [
    url(r"^admin/", admin.site.urls),
    url(r"", include(datasets_urls, namespace="datasets")),
]
