from django.conf import settings

from common.pagination import paginate

from pybb.views import load_last_post 

def forum_details(forum, request):
    """
    Return data which usually used on Forum Details page.

    This function is useful if you want to display topics from some
    forum outside the forum. For example, news section on the website
    could be powered by content from some subforum. In this case each
    News item will be a ``Topic`` instance and all comments will be
    ``Post`` items.

    Args:
        forum: the ``pybb.models.Forum`` instance
        request: ``Request`` object
    """

    topics = forum.topics.order_by('-sticky', '-updated').select_related()
    page = paginate(topics, request, settings.PYBB_FORUM_PAGE_SIZE)
    load_last_post(page.object_list)

    return {'forum': forum,
            'page': page,
            }
