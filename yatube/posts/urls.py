from django.urls import path


from . import views

app_name = 'posts'

urlpatterns = [
    path('', views.index, name='index'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('posts/<int:post_id>/', views.post_detail, name='post_detail'),
    path('group/<slug:slug>/', views.group_posts, name='group_list'),
    path('create/', views.post_create, name='post_create'),
    path('create_group', views.group_create, name='group_create'),
    path('posts/<post_id>/edit/', views.post_edit, name='post_edit'),
    path(
        'posts/<int:post_id>/comment/',
        views.add_comment,
        name='add_comment'
    ),
    path('follow/', views.follow_index, name='follow_index'),
    path('most_popular/', views.most_popular_index, name='most_popular_index'),
    path(
        'profile/<str:username>/follow/',
        views.profile_follow,
        name='profile_follow'
    ),
    path(
        'profile/<str:username>/unfollow/',
        views.profile_unfollow,
        name='profile_unfollow'
    ),
    path('like/', views.like_index, name='like_index'),
    path(
        'posts/<int:post_id>/like/',
        views.post_like,
        name='post_like'
    ),
    path(
        'posts/<int:post_id>/unlike/',
        views.post_unlike,
        name='post_unlike'
    ),
   path('search/', views.search_results, name='search_results'),

]
