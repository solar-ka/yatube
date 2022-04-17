from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, GroupForm, PostForm
from .models import Comment, Follow, Group, Like, Post, User
from .utils import annotate, likes_on_page, paginate


def index(request):
    template = 'posts/index.html'
    posts = Post.objects.select_related('author').all()
    page_obj = paginate(posts, request)
    page_obj = likes_on_page(page_obj, request.user)
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)


def group_posts(request, slug):
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    posts = Post.objects.select_related('group').filter(group=group)
    page_obj = paginate(posts, request)
    page_obj = likes_on_page(page_obj, request.user)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    template = 'posts/profile.html'
    author = get_object_or_404(User, username=username)
    posts = Post.objects.select_related('author').filter(author=author)
    page_obj = paginate(posts, request)
    page_obj = likes_on_page(page_obj, request.user)
    posts_count = posts.count()
    user = request.user
    if user.is_authenticated and user != author:
        following = Follow.objects.filter(
            user=user, author=author
        ).exists()
    else:
        following = False
    context = {
        'author': author,
        'page_obj': page_obj,
        'posts_count': posts_count,
        'following': following,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, id=post_id)
    author = post.author
    num_author_posts = Post.objects.filter(author=author).count()
    comment_form = CommentForm(request.POST or None)
    comments = Comment.objects.filter(post=post)
    likes = Like.objects.filter(post=post).count()
    now_liker = False
    if request.user.is_authenticated and Like.objects.filter(
        post=post, user=request.user
    ).exists():
        now_liker = True
    context = {
        'author': author,
        'post': post,
        'posts_count': num_author_posts,
        'form': comment_form,
        'comments': comments,
        'likes': likes,
        'now_liker': now_liker,
    }
    return render(request, template, context)


@login_required
def post_create(request):
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', post.author)
    return render(request, 'posts/post_create.html', {'form': form})

@login_required
def group_create(request):
    form = GroupForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if form.is_valid():
        group = form.save(commit=False)
        group.creator = request.user
        group.save()
        return redirect('posts:group_list', group.slug)
    return render(request, 'posts/group_create.html', {'form': form})

@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if not form.is_valid():
        if request.user == post.author:
            template = 'posts/post_create.html'
            context = {
                'form': form,
                'is_edit': True
            }
            return render(request, template, context)
        return redirect('posts:post_detail', post.id)
    post = form.save()
    return redirect('posts:post_detail', post.id)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    template = 'posts/follow.html'
    user = request.user
    posts = Post.objects.filter(author__following__user=user)
    page_obj = paginate(posts, request)
    page_obj = likes_on_page(page_obj, request.user)
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)

def most_popular_index(request):
    template = 'posts/most_popular_index.html'
    posts = Post.objects.all()
    posts = annotate(posts)
    posts = posts.order_by('-num_likes', '-pub_date')
    page_obj = paginate(posts, request)
    page_obj = likes_on_page(page_obj, request.user)
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)

@login_required
def like_index(request):
    template = 'posts/like.html'
    user = request.user
    posts = Post.objects.filter(likes__user=user)
    page_obj = paginate(posts, request)
    page_obj = likes_on_page(page_obj, request.user)
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)

@login_required
def profile_follow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    now_follower = Follow.objects.filter(user=user, author=author).exists()
    if user != author and not now_follower:
        Follow.objects.create(user=user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    now_follower = Follow.objects.filter(user=user, author=author).exists()
    if now_follower:
        follow = Follow.objects.get(user=user, author=author)
        follow.delete()
    return redirect('posts:profile', username=username)

@login_required
def post_like(request, post_id):
    user = request.user
    post = get_object_or_404(Post, id=post_id)
    now_liker = Like.objects.filter(user=user, post=post).exists()
    if not now_liker:
        Like.objects.create(user=user, post=post)
    return redirect('posts:post_detail', post_id=post_id)

@login_required
def post_unlike(request, post_id):
    user = request.user
    post = get_object_or_404(Post, id=post_id)
    now_liker = Like.objects.filter(user=user, post=post).exists()
    if now_liker:
        like = Like.objects.get(user=user, post=post)
        like.delete()
    return redirect('posts:post_detail', post_id=post_id)



def search_results(request):
    template = 'posts/search_results.html'
    query = request.GET.get('q')
    data_type = request.GET.get('type', 'posts')
    posts=[]
    authors=[]
    if data_type == 'authors':
        authors = User.objects.filter(
            Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
        )
        page_obj = paginate(authors, request)
        search_authors = True
        search_posts = False
    elif data_type == 'posts':   
        posts = Post.objects.filter(
            text__icontains=query
        )
        page_obj = paginate(posts, request)
        page_obj = likes_on_page(page_obj, request.user)
        search_authors = False
        search_posts = True
    else:
        search_authors = False
        search_posts = False
  
    context = {
        'page_obj': page_obj,
        'query': query,
        'search_authors': search_authors,
        'search_posts': search_posts,
    }
    return render(request, template, context)
