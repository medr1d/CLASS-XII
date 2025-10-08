from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from homepage.sitemaps import generate_sitemap_xml

urlpatterns = [
    path('', include(('homepage.urls', 'homepage'), namespace='homepage')),
    path('auth/', include('auth_app.urls')),
    path('sitemap.xml', generate_sitemap_xml, name='sitemap'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
