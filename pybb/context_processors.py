from urlparse import urljoin

from django.conf import settings

def pybb(request):

    media_url = urljoin(settings.MEDIA_URL, 'pybb/')
    
    return {'PYBB_MEDIA_URL': media_url,
            }
