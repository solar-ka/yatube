from django.core.paginator import Paginator
from django.db.models import Count
from yatube.settings import NUM_OF_POSTS_ON_PAGE

from .models import Post


def paginate(posts, request):
    paginator = Paginator(posts, NUM_OF_POSTS_ON_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


def annotate(posts):
    posts = posts.annotate(num_likes=Count('likes')).all()
    return posts

def likes_on_page(page_obj, user):
    posts_id = []
    for post in page_obj:
        posts_id.append(post.id)
    liked_posts = Post.objects.filter(
        likes__user__username=user, likes__post__id__in=posts_id
    )
    for post in page_obj:
        if post in liked_posts:
            post.is_like = True
        else:
            post.is_like = False
    return page_obj
