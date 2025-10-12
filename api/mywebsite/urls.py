from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from homepage.sitemaps import generate_sitemap_xml
from django.views.generic.base import RedirectView

urlpatterns = [
    path('', include(('homepage.urls', 'homepage'), namespace='homepage')),
    path('auth/', include('auth_app.urls')),
    path('sitemap.xml', generate_sitemap_xml, name='sitemap'),
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.ico', permanent=True)),
    path('favicon.png', RedirectView.as_view(url='/static/images/favicon.ico', permanent=True)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
