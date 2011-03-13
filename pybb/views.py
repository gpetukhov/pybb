# coding: utf-8
import math
import re
from datetime import datetime
from markdown import Markdown
try:
    import pytils
    pytils_enabled = True
except ImportError:
    pytils_enabled = False

from django.shortcuts import get_object_or_404, get_list_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse,\
                        HttpResponseNotFound, Http404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import connection
from django.utils.translation import ugettext_lazy as _

from common.decorators import render_to, ajax
from common.orm import load_related
from common.pagination import paginate

from pybb.markups import mypostmarkup
from pybb.util import quote_text, set_language, urlize
from pybb.models import Category, Forum, Topic, Post, Profile, \
                        Attachment, MARKUP_CHOICES
from pybb.forms import  AddPostForm, EditPostForm, EditHeadPostForm, \
                        EditProfileForm, UserSearchForm
from pybb.read_tracking import update_read_tracking
from pybb.templatetags.pybb_tags import pybb_editable_by, pybb_moderated_by



def load_last_post(objects):
    """
    Get list of topics/forums and find the recent post in
    each topic/forum. Also extract author of the post.
    """

    pk_list = [x.last_post_id for x in objects]
    qs = Post.objects.filter(pk__in=pk_list).select_related('user')
    posts = dict((x.pk, x) for x in qs)
    for obj in objects:
        obj.last_post = posts.get(obj.last_post_id)


@render_to('pybb/index.html')
def index(request):
    """
    Display list of categories and forums in each category.
    """

    cats = list(Category.objects.all())
    cat_map = dict((x.pk, x) for x in cats)
    for cat in cats:
        cat.cached_forums = []
    forums = list(Forum.objects.all())
    load_last_post(forums)
    for forum in forums:
        cat_map[forum.category_id].cached_forums.append(forum)
    return {'cats': cats,
            }


@render_to('pybb/category_details.html')
def category_details(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    forums = category.forums.all()
    load_last_post(forums)
    category.cached_forums = forums

    return {'category': category,
            }


@render_to('pybb/forum_details.html')
def forum_details(request, forum_id):
    forum = get_object_or_404(Forum, pk=forum_id)
    topics = forum.topics.order_by('-sticky', '-updated').select_related()
    page = paginate(topics, request, settings.PYBB_FORUM_PAGE_SIZE)
    load_last_post(page.object_list)

    return {'forum': forum,
            'page': page,
            }


@render_to('pybb/topic_details.html')
def topic_details(request, topic_id):
    try:
        topic = Topic.objects.select_related().get(pk=topic_id)
    except Topic.DoesNotExist:
        raise Http404()

    topic.views += 1
    topic.save()

    if request.user.is_authenticated():
        update_read_tracking(topic, request.user)
	
    if settings.PYBB_FREEZE_FIRST_POST:
        first_post = topic.head
    else:
        first_post = None

    form = AddPostForm(topic=topic)

    moderator = (request.user.is_superuser or
                 request.user in topic.forum.moderators.all())
    subscribed = (request.user.is_authenticated() and
                  request.user in topic.subscribers.all())

    posts = topic.posts.all()

    page = paginate(posts, request, settings.PYBB_TOPIC_PAGE_SIZE)

    users = User.objects.filter(pk__in=
        set(x.user_id for x in page.object_list)).select_related("pybb_profile")
    users = dict((user.pk, user) for user in users)

    for post in page.object_list:
        post.user = users.get(post.user_id)

    load_related(page.object_list, Attachment.objects.all(), 'post')

    return {'topic': topic,
            'last_post': topic.last_post,
            'first_post': first_post,
            'form': form,
            'moderator': moderator,
            'subscribed': subscribed,
            'posts': page.object_list,
            'page': page,
            }


@login_required
@render_to('pybb/post_add.html')
def post_add(request, forum_id, topic_id):
    forum = None
    topic = None

    if forum_id:
        forum = get_object_or_404(Forum, pk=forum_id)
    elif topic_id:
        topic = get_object_or_404(Topic, pk=topic_id)

    if (topic and topic.closed) or request.user.pybb_profile.is_banned():
        return HttpResponseRedirect(topic.get_absolute_url())

    try:
        quote_id = int(request.GET.get('quote_id'))
    except TypeError:
        quote = ''
    else:
        post = get_object_or_404(Post, pk=quote_id)
        quote = quote_text(post.body_text,
                           request.user.pybb_profile.markup,
                           post.user.username)

    ip = request.META.get('REMOTE_ADDR', '')
    form_kwargs = dict(topic=topic, forum=forum, user=request.user,
                       ip=ip, initial={'body': quote})
    if request.method == 'POST':
        form = AddPostForm(request.POST, request.FILES, **form_kwargs)
    else:
        form = AddPostForm(**form_kwargs)

    if form.is_valid():
        post = form.save();
        return redirect(post)

    return {'form': form,
            'topic': topic,
            'forum': forum,
            }


@render_to('pybb/user_details.html')
def user_details(request, username):
    user = get_object_or_404(User, username=username)
    topic_count = Topic.objects.filter(user=user).count()

    return {'profile': user,
            'topic_count': topic_count,
            }


@render_to('pybb/user_details_topics.html')
def user_details_topics(request, username):
    user = get_object_or_404(User, username=username)
    topics = Topic.objects.filter(user=user).order_by('-created')
    page = paginate(topics, request, settings.PYBB_TOPIC_PAGE_SIZE)

    return {'profile': user,
            'page': page,
            }


def post_details(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    count = post.topic.posts.filter(created__lt=post.created).count() + 1
    page = math.ceil(count / float(settings.PYBB_TOPIC_PAGE_SIZE))
    url = '%s?page=%d#post-%d' % (reverse('pybb_topic_details', args=[post.topic.id]), page, post.id)
    return redirect(url)


@login_required
@render_to('pybb/profile_edit.html')
def profile_edit(request):

    form_kwargs = dict(instance=request.user.pybb_profile)
    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, **form_kwargs)
    else:
        form = EditProfileForm(**form_kwargs)

    if form.is_valid():
        profile = form.save()
        set_language(request, profile.language)
        return redirect('pybb_profile_edit')

    return {'form': form,
            'profile': request.user.pybb_profile,
            }


@login_required
@render_to('pybb/post_edit.html')
def post_edit(request, post_id):

    post = get_object_or_404(Post, pk=post_id)

    if not pybb_editable_by(post, request.user) \
    or request.user.pybb_profile.is_banned():
        return redirect(post)

    head_post_id = post.topic.posts.order_by('created')[0].id
    form_kwargs = dict(instance=post, initial={'title': post.topic.name})

    if post.id == head_post_id:
        form_class = EditHeadPostForm
    else:
        form_class = EditPostForm

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, **form_kwargs)
    else:
        form = form_class(**form_kwargs)

    if form.is_valid():
        post = form.save()
        return redirect(post)

    return {'form': form,
            'post': post,
            }


@login_required
def topic_stick(request, topic_id):

    topic = get_object_or_404(Topic, pk=topic_id)
    if pybb_moderated_by(topic, request.user):
        if not topic.sticky:
            topic.sticky = True
            topic.save()
    return redirect(topic)


@login_required
def topic_unstick(request, topic_id):
    topic = get_object_or_404(Topic, pk=topic_id)
    if pybb_moderated_by(topic, request.user):
        if topic.sticky:
            topic.sticky = False
            topic.save()
    return redirect(topic)


@login_required
@render_to('pybb/post_delete.html')
def post_delete(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    last_post = post.topic.posts.order_by('-created')[0]

    allowed = False
    if request.user.is_superuser or\
        request.user in post.topic.forum.moderators.all() or \
        (post.user == request.user and post == last_post):
        allowed = True

    if not allowed:
        return redirect(post)

    if 'POST' == request.method:
        topic = post.topic
        forum = post.topic.forum
        post.delete()

        try:
            Topic.objects.get(pk=topic.id)
        except Topic.DoesNotExist:
            return redirect(forum)
        else:
            return redirect(topic)
    else:
        return {'post': post,
                }


@login_required
def topic_close(request, topic_id):
    topic = get_object_or_404(Topic, pk=topic_id)
    if pybb_moderated_by(topic, request.user):
        if not topic.closed:
            topic.closed = True
            topic.save()
    return redirect(topic)



@login_required
def topic_open(request, topic_id):
    topic = get_object_or_404(Topic, pk=topic_id)
    if pybb_moderated_by(topic, request.user):
        if topic.closed:
            topic.closed = False
            topic.save()
    return redirect(topic)



@login_required
@render_to('pybb/topic_merge.html')
def topic_merge(request):
    topics_ids = request.GET.getlist('topic')
    topics = get_list_or_404(Topic, pk__in=topics_ids)

    for topic in topics:
        if not pybb_moderated_by(topic, request.user):
            # TODO: show error message: no permitions for edit this topic
            return HttpResponseRedirect(topic.get_absolute_url())

    if len(topics) < 2:
        return {'topics': topics}

    posts = get_list_or_404(Post, topic__in=topics_ids)
    main = int(request.POST.get("main", 0))

    if main and main in (topic.id for topic in topics):
        for topic in topics:
            if topic.id == main:
                main_topic = topic

        for post in posts:
            if post.topic_id != main_topic.id:
                post.topic = main_topic
                post.save()

        main_topic.update_post_count()
        main_topic.forum.update_post_count()

        for topic in topics:
            if topic.id != main:
                forum = topic.forum
                topic.delete()
                forum.update_post_count()

        return redirect(main_topic)

    return {'posts': posts,
            'topics': topics,
            'topic': topics[0],
            }


@render_to('pybb/user_list.html')
def user_list(request):
    users = User.objects.order_by('username')
    form = UserSearchForm(request.GET)
    users = form.filter(users)

    page = paginate(users, request, settings.PYBB_USERS_PAGE_SIZE)

    return {'page': page,
            'form': form,
            }


@login_required
def subscription_delete(request, topic_id):
    topic = get_object_or_404(Topic, pk=topic_id)
    topic.subscribers.remove(request.user)
    if 'from_topic' in request.GET:
        return redirect(topic)
    else:
        return redirect('pybb_edit_profile')


@login_required
def subscription_add(request, topic_id):
    topic = get_object_or_404(Topic, pk=topic_id)
    topic.subscribers.add(request.user)
    return redirect('pybb_topic_details', topic.id)


@login_required
def attachment_details(request, hash):
    attachment = get_object_or_404(Attachment, hash=hash)
    file_obj = file(attachment.get_absolute_path())
    # without it mod_python chokes with error that content_type must be string
    return HttpResponse(file_obj, content_type=str(attachment.content_type))


@login_required
@ajax
def post_ajax_preview(request):
    content = request.POST.get('content')
    markup = request.user.pybb_profile.markup

    if not markup in dict(MARKUP_CHOICES).keys():
        return {'error': 'Invalid markup'}

    if not content:
        return {'content': ''}

    if markup == 'bbcode':
        html = mypostmarkup.markup(content, auto_urls=False)
    elif markup == 'markdown':
        instance = Markdown(safe_mode='escape')
        html = unicode(instance.convert(content))

    html = urlize(html)

    return {'content': html,
            }
