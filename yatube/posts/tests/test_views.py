import datetime
import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from yatube.settings import NUM_OF_POSTS_ON_PAGE

from ..models import Comment, Follow, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        cls.user_author = User.objects.create_user(username='author')
        cls.group_1 = Group.objects.create(
            title='Тестовая группа 1',
            slug='test-slug1',
            description='Тестовое описание 1',
        )
        cls.group_2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug2',
            description='Тестовое описание 2',
        )
        cls.post = Post.objects.create(
            author=cls.user_author,
            text='Тестовый текст',
        )
        cls.post.pub_date = datetime.datetime(2021, 1, 1)
        cls.post.save()
        cls.post_in_group_1 = Post.objects.create(
            author=cls.user_author,
            text='Тестовый текст в группе 1',
            group=cls.group_1,
            image=uploaded,
        )
        cls.post_in_group_1.pub_date = datetime.datetime(2021, 1, 2)
        cls.post_in_group_1.save()
        cls.post_in_group_2 = Post.objects.create(
            author=cls.user_author,
            text='Тестовый текст в группе 2',
            group=cls.group_2,
        )
        cls.post_in_group_2.pub_date = datetime.datetime(2021, 1, 3)
        cls.post_in_group_2.save()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_author)

    def tearDown(self):
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={
                'slug': self.group_1.slug
            }): 'posts/group_list.html',
            reverse('posts:profile', kwargs={
                'username': self.user_author.username
            }): 'posts/profile.html',
            reverse('posts:post_detail', kwargs={
                'post_id': self.post.id
            }): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/post_create.html',
            reverse('posts:post_edit', kwargs={
                'post_id': self.post.id
            }): 'posts/post_create.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def check_context(self, list_post_fields, posts_on_page):
        """Вспомогательня функция проверки контекста.

        Используется для тестов index, group_list, profile, post_detail"""
        for i in range(len(posts_on_page)):
            post_fields = list_post_fields[i]
            for value, expected in post_fields.items():
                with self.subTest(post_and_field=f'{i} and {value}'):
                    post_field = getattr(posts_on_page[i], value)
                    self.assertEqual(post_field, expected)

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом"""
        response = self.authorized_client.get(reverse('posts:index'))
        posts_on_page = response.context.get('page_obj')
        list_post_fields = [
            {
                'author': self.user_author,
                'text': self.post_in_group_2.text,
                'group': self.group_2,
                'id': self.post_in_group_2.id
            },
            {
                'author': self.user_author,
                'text': self.post_in_group_1.text,
                'group': self.group_1,
                'id': self.post_in_group_1.id,
                'image': 'posts/small.gif',
            },
            {
                'author': self.user_author,
                'text': self.post.text,
                'group': None,
                'id': self.post.id
            }
        ]
        self.check_context(list_post_fields, posts_on_page)

    def test_cache_index(self):
        """Главная страница кэшируется"""
        response_1 = self.authorized_client.get(reverse('posts:index'))
        deleted_post = Post.objects.get(id=self.post.id)
        deleted_post.delete()
        response_2 = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response_1.content, response_2.content)
        cache.clear()
        response_3 = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response_1.content, response_3.content)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом"""
        response = self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': self.user_author.username}))
        posts_on_page = response.context.get('page_obj')
        self.assertEqual(response.context.get('author'), self.user_author)
        self.assertEqual(
            response.context.get('posts_count'),
            Post.objects.filter(author=self.user_author).count()
        )
        list_post_fields = [
            {
                'author': self.user_author,
                'text': self.post_in_group_2.text,
                'group': self.group_2,
                'id': self.post_in_group_2.id

            },
            {
                'author': self.user_author,
                'text': self.post_in_group_1.text,
                'group': self.group_1,
                'id': self.post_in_group_1.id,
                'image': 'posts/small.gif',
            },
            {
                'author': self.user_author,
                'text': self.post.text,
                'group': None,
                'id': self.post.id
            }
        ]
        self.check_context(list_post_fields, posts_on_page)

    def test_group_list_show_correct_context(self):
        """Шаблон group_list первой группы сформирован с правильным контекстом.

        Проверяет, посты группы 1
        """
        response = self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group_1.slug}))
        posts_on_page = response.context.get('page_obj')
        context_group = response.context.get('group')
        self.assertEqual(context_group, self.group_1)
        list_post_fields = [
            {
                'author': self.user_author,
                'text': self.post_in_group_1.text,
                'group': self.group_1,
                'id': self.post_in_group_1.id,
                'image': 'posts/small.gif',
            },
        ]
        self.check_context(list_post_fields, posts_on_page)

    def test_another_group_list_show_correct_context(self):
        """Шаблон group_list второй группы сформирован с правильным контекстом.

        Проверяет, посты группы 2
        """
        response = self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group_2.slug}))
        posts_on_page = response.context.get('page_obj')
        context_group = response.context.get('group')
        self.assertEqual(context_group, self.group_2)
        list_post_fields = [
            {
                'author': self.user_author,
                'text': self.post_in_group_2.text,
                'group': self.group_2,
                'id': self.post_in_group_2.id
            },
        ]
        self.check_context(list_post_fields, posts_on_page)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post_in_group_1.id}))
        post = [response.context.get('post')]
        post_fields = [
            {
                'author': self.user_author,
                'text': self.post_in_group_1.text,
                'group': self.group_1,
                'id': self.post_in_group_1.id,
                'image': 'posts/small.gif',
            }
        ]
        self.check_context(post_fields, post)

    def test_post_detail_contain_comment_form(self):
        """Шаблон post_detail содержит форму создания комментария"""
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post_in_group_1.id}))
        form = response.context.get('form')
        comment_fields = {
            'text': forms.fields.CharField,
        }
        for value, expected in comment_fields.items():
            with self.subTest(field=value):
                form_field = form.fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_detail_content_comments(self):
        """Шаблон post_detail сожержит комментарии к посту"""
        self.comment = Comment.objects.create(
            post=self.post_in_group_1,
            author=self.user_author,
            text='Текст комментария',
        )
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post_in_group_1.id}))
        comment = [response.context.get('comments')][0]
        comment_fields = [
            {
                'post': self.post_in_group_1,
                'author': self.user_author,
                'text': self.comment.text,
            }
        ]
        self.check_context(comment_fields, comment)

    def check_context_create_edit(self, response):
        """Вспомогательная функция проверки контекста в edit и create"""
        form = response.context.get('form')
        post_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in post_fields.items():
            with self.subTest(field=value):
                form_field = form.fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_create_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.check_context_create_edit(response)

    def test_post_edit_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id}))
        self.check_context_create_edit(response)


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='just_user')
        cls.user_author = User.objects.create_user(username='author')

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_profile_follow(self):
        """Авторизованный пользователь может подписаться на автора."""
        pre_follower = Follow.objects.filter(
            user=self.user, author=self.user_author
        ).exists()
        self.assertFalse(pre_follower)
        self.authorized_client.get(reverse(
            'posts:profile_follow', kwargs={'username': self.user_author}
        ))
        after_follower = Follow.objects.filter(
            user=self.user, author=self.user_author
        ).exists()
        self.assertTrue(after_follower)

    def test_profile_unfollow(self):
        """Авторизованный пользователь может отписаться от автора."""
        Follow.objects.create(user=self.user, author=self.user_author)
        pre_follower = Follow.objects.filter(
            user=self.user, author=self.user_author
        ).exists()
        self.assertTrue(pre_follower)
        self.authorized_client.get(reverse(
            'posts:profile_unfollow', kwargs={'username': self.user_author}
        ))
        after_follower = Follow.objects.filter(
            user=self.user, author=self.user_author
        ).exists()
        self.assertFalse(after_follower)

    def test_follow_index(self):
        """При создании автором новой записи, она появляется у подписчика."""
        Follow.objects.create(user=self.user, author=self.user_author)
        self.new_post = Post.objects.create(
            text='пост, который появится у подписчика',
            author=self.user_author
        )
        self.user_non_follower = User.objects.create_user(
            username='non_follower'
        )
        self.authorized_non_follower = Client()
        self.authorized_non_follower.force_login(self.user_non_follower)
        response_follower = self.authorized_client.get(reverse(
            'posts:follow_index'))
        self.assertTrue(self.new_post in response_follower.context['page_obj'])
        response_non_follower = self.authorized_non_follower.get(reverse(
            'posts:follow_index'
        ))
        self.assertFalse(self.new_post in response_non_follower.context[
            'page_obj']
        )


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.group_1 = Group.objects.create(
            title='Тестовая группа 1',
            slug='test-slug1',
            description='Тестовое описание 1',
        )
        cls.posts = []
        cls.NUM_OF_POSTS_IN_TEST = 13
        for i in range(cls.NUM_OF_POSTS_IN_TEST):
            cls.posts.append(Post(
                text=f'Тестовый текст в посте {i}',
                author=cls.user,
                group=cls.group_1)
            )
        Post.objects.bulk_create(cls.posts)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def tearDown(self):
        cache.clear()

    def test_first_page_contains_ten_records(self):
        """Количество постов на первой странице равно 10"""
        urls_for_paginator = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': 'test-slug1'}),
            reverse('posts:profile', kwargs={'username': self.user.username})
        ]
        for url in urls_for_paginator:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(
                    len(response.context['page_obj']), NUM_OF_POSTS_ON_PAGE
                )

    def test_second_page_contains_three_records(self):
        """Количество постов на второй странице равно 3"""
        urls_for_paginator = [
            reverse('posts:index') + '?page=2',
            reverse('posts:group_list', kwargs={
                'slug': self.group_1.slug
            }) + '?page=2',
            reverse('posts:profile', kwargs={
                'username': self.user.username
            }) + '?page=2'
        ]
        remainder_posts = self.NUM_OF_POSTS_IN_TEST - NUM_OF_POSTS_ON_PAGE
        if remainder_posts <= 0:
            num_of_post_on_page_2 = 0
        elif remainder_posts >= NUM_OF_POSTS_ON_PAGE:
            num_of_post_on_page_2 = NUM_OF_POSTS_ON_PAGE
        else:
            num_of_post_on_page_2 = remainder_posts
        for url in urls_for_paginator:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(
                    len(response.context['page_obj']), num_of_post_on_page_2
                )
