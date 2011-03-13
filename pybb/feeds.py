from django.contrib.syndication.views import Feed
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.shortcuts import get_object_or_404

from pybb.models import Post, Topic, Forum


class PybbFeed(Feed):
    def link(self):
        return reverse('pybb_index')

    def item_guid(self, obj):
        return str(obj.id)

    def item_pubdate(self, obj):
        return obj.created


class LatestPostFeed(PybbFeed):
    title = _('Latest posts on forum')
    description = _('Latest posts on forum')
    title_template = 'pybb/feeds/posts_title.html'
    description_template = 'pybb/feeds/posts_description.html'

    def items(self):
        return Post.objects.order_by('-created')[:15]


class LatestTopicFeed(PybbFeed):
    title = _('Latest topics on forum')
    description = _('Latest topics on forum')
    title_template = 'pybb/feeds/topics_title.html'
    description_template = 'pybb/feeds/topics_description.html'

    def items(self):
        return Topic.objects.order_by('-created')[:15]


class PybbForumFeed(PybbFeed):
    title_template = 'pybb/feeds/forum_post_title.html'
    description_template = 'pybb/feeds/forum_post_description.html'

class ForumFeed(PybbForumFeed):
    def title(self, obj):
        return _(u'Latest topics in %s forum' % obj)

    def items(self, obj):
        return obj.topics.all().order_by('-created')[:15]


class ForumByTagFeed(ForumFeed):
    def get_object(self, request, slug):
        return get_object_or_404(Forum, slug=slug)


class ForumByIdFeed(ForumFeed):
    def get_object(self, request, pk):
        return get_object_or_404(Forum, pk=pk)
