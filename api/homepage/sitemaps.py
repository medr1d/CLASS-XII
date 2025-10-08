from django.http import HttpResponse
from django.urls import reverse
from django.template import Template, Context
from datetime import datetime


def generate_sitemap_xml(request):
    """Generate sitemap XML without using Django's Sites framework"""
    
    # Get the current domain from the request
    domain = request.get_host()
    protocol = 'https' if request.is_secure() else 'http'
    base_url = f"{protocol}://{domain}"
    
    # Define all URLs to include in sitemap
    urls = [
        {
            'loc': f"{base_url}{reverse('home')}",
            'changefreq': 'monthly',
            'priority': '1.0',
            'lastmod': datetime.now().strftime('%Y-%m-%d')
        },
        {
            'loc': f"{base_url}{reverse('python_environment')}",
            'changefreq': 'monthly', 
            'priority': '0.8',
            'lastmod': datetime.now().strftime('%Y-%m-%d')
        },
        {
            'loc': f"{base_url}{reverse('timer')}",
            'changefreq': 'weekly',
            'priority': '0.9',
            'lastmod': datetime.now().strftime('%Y-%m-%d')
        },
        {
            'loc': f"{base_url}{reverse('settings')}",
            'changefreq': 'monthly',
            'priority': '0.7',
            'lastmod': datetime.now().strftime('%Y-%m-%d')
        },
        {
            'loc': f"{base_url}{reverse('azure_robot')}",
            'changefreq': 'monthly',
            'priority': '0.8',
            'lastmod': datetime.now().strftime('%Y-%m-%d')
        },
        {
            'loc': f"{base_url}{reverse('auth_app:signup')}",
            'changefreq': 'yearly',
            'priority': '0.6',
            'lastmod': datetime.now().strftime('%Y-%m-%d')
        },
        {
            'loc': f"{base_url}{reverse('auth_app:login')}",
            'changefreq': 'yearly',
            'priority': '0.6',
            'lastmod': datetime.now().strftime('%Y-%m-%d')
        }
    ]
    
    # Generate XML sitemap
    xml_template = Template("""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{% for url in urls %}
    <url>
        <loc>{{ url.loc }}</loc>
        <lastmod>{{ url.lastmod }}</lastmod>
        <changefreq>{{ url.changefreq }}</changefreq>
        <priority>{{ url.priority }}</priority>
    </url>
{% endfor %}
</urlset>""")
    
    xml_content = xml_template.render(Context({'urls': urls}))
    
    response = HttpResponse(xml_content, content_type='application/xml')
    response['Content-Disposition'] = 'inline; filename="sitemap.xml"'
    
    return response


# Legacy classes for when Sites framework is working (kept for future use)
class StaticViewSitemap:
    """Sitemap for static pages (not used currently due to Sites framework requirement)"""
    priority = 0.8
    changefreq = 'monthly'
    protocol = 'https'

    def items(self):
        return [
            'home',  # Homepage
            'python_environment',  # Python terminal
            'timer',  # Study timer
            'settings',  # Settings page
            'azure_robot',  # AI assistant
        ]

    def location(self, item):
        return reverse(item)


class AuthViewSitemap:
    """Sitemap for authentication pages (not used currently due to Sites framework requirement)"""
    priority = 0.6
    changefreq = 'yearly'
    protocol = 'https'

    def items(self):
        return [
            'auth_app:signup',  # Signup page
            'auth_app:login',   # Login page
        ]

    def location(self, item):
        return reverse(item)