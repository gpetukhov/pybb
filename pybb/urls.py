from django.conf.urls.defaults import *

from pybb import views
from pybb.feeds import LastPosts, LastTopics


feeds = {
    'posts': LastPosts,
    'topics': LastTopics,
}

urlpatterns = patterns('',
    # Syndication feeds
    url('^feeds/(?P<url>.*)/$', 'django.contrib.syndication.views.feed',
        {'feed_dict': feeds}, name='pybb_feed'),
)

urlpatterns += patterns('pybb.views',
    # Index, Category, Forum
    url('^$', 'index', name='pybb_index'),
    url('^category/(\d+)/$', 'category_details', name='pybb_category_details'),
    url('^forum/(\d+)/$', 'forum_details', name='pybb_forum_details'),

    # User
    url('^user/$', 'user_list', name='pybb_user_list'),
    url('^user/([^/]+)/$', 'user_details', name='pybb_user_details'),
    url('^user/([^/]+)/topics/$', 'user_details_topics', name='pybb_user_details_topics'),

    # Profile
    url('^profile/edit/$', 'profile_edit', name='pybb_profile_edit'),

    # Topic
    url('^topic/(\d+)/$', 'topic_details', name='pybb_topic_details'),
    url('^topic/(\d+)/stick/$', 'topic_stick', name='pybb_topic_stick'),
    url('^topic/(\d+)/unstick/$', 'topic_unstick', name='pybb_topic_unstick'),
    url('^topic/(\d+)/close/$', 'topic_close', name='pybb_topic_close'),
    url('^topic/(\d+)/open/$', 'topic_open', name='pybb_topic_open'),
    url('^topic/merge/$', 'topic_merge', name='pybb_topic_merge'),

    # Add topic/post
    url('^forum/(?P<forum_id>\d+)/topic/add/$', 'post_add',
        {'topic_id': None}, name='pybb_topic_add'),
    url('^topic/(?P<topic_id>\d+)/post/add/$', 'post_add',
        {'forum_id': None}, name='pybb_post_add'),

    # Post
    url('^post/(\d+)/$', 'post_details', name='pybb_post_details'),
    url('^post/(\d+)/edit/$', 'post_edit', name='pybb_post_edit'),
    url('^post/(\d+)/delete/$', 'post_delete', name='pybb_post_delete'),

    # Attachment
    url('^attachment/(\w+)/$', 'attachment_details', name='attachment_details'),

    # Subscription
    url('^subscription/topic/(\d+)/delete/$',
        'subscription_delete', name='pybb_subscription_delete'),
    url('^subscription/topic/(\d+)/add/$',
        'subscription_add', name='pybb_subscription_add'),

    # API
    url('^api/post_ajax_preview/$', 'post_ajax_preview', name='pybb_post_ajax_preview'),
)
