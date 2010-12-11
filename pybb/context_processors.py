from urlparse import urljoin

from django.conf import settings

def pybb(request):
    media_url = urljoin(settings.MEDIA_URL, 'pybb/')
    
    if request.user.is_authenticated():
        markup = request.user.pybb_profile.markup
    else:
        markup = settings.PYBB_DEFAULT_MARKUP

    return {'PYBB_MEDIA_URL': media_url,
            'PYBB_MARKUP': markup,
            }
