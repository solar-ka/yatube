from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.core.cache import cache

from ..models import Group, Post

User = get_user_model()


class StaticURLTests(TestCase):
    def tearDown(self):
        cache.clear()

    def test_homepage(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, HTTPStatus.OK)


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user_author,
            text='Тестовый текст',
        )

    def setUp(self):
        self.authorized_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client.force_login(self.user)

        # Создаем клиент для автора поста
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.user_author)

    def tearDown(self):
        cache.clear()

    def test_urls_exists_to_unauthorized_user(self):
        """Доступность адресов для неавторизованного пользователя."""
        url_responses_code = {
            '/': HTTPStatus.OK,
            f'/group/{self.group.slug}/': HTTPStatus.OK,
            f'/profile/{self.user_author.username}/': HTTPStatus.OK,
            f'/posts/{self.post.id}/': HTTPStatus.OK,
            f'/posts/{self.post.id}/edit/': HTTPStatus.FOUND,
            f'/posts/{self.post.id}/comment/': HTTPStatus.FOUND,
            '/create/': HTTPStatus.FOUND,
            '/unexpected-address/': HTTPStatus.NOT_FOUND
        }
        for address, code in url_responses_code.items():
            with self.subTest(address=address):
                response = self.client.get(address)
                self.assertEqual(response.status_code, code)

    def test_urls_redirect_to_unauthorized_user(self):
        """Редирект неавторизованных пользователей на страницу авторизации.

        Срабатывает при попытке редактировать, комментировать или создать пост.
        """
        url_redirect_unauth = {
            f'/posts/{self.post.id}/edit/':
                f'/auth/login/?next=/posts/{self.post.id}/edit/',
            '/create/':
                '/auth/login/?next=/create/',
            f'/posts/{self.post.id}/comment/':
                f'/auth/login/?next=/posts/{self.post.id}/comment/'
        }
        for address, redirect in url_redirect_unauth.items():
            with self.subTest(address=address):
                response = self.client.get(address, follow=True)
                self.assertRedirects(response, redirect)

    def test_urls_redirect_non_author(self):
        """Редирект не автора поста на промотр поста вместо редактирования."""
        response = self.authorized_client.get(
            f'/posts/{self.post.id}/edit/', follow=True)
        self.assertRedirects(response, '/posts/1/')

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон.

        Проверяется для авторизованого пользователя, являющегося автором поста.
        """
        url_templates_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user_author.username}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/posts/{self.post.id}/edit/': 'posts/post_create.html',
            '/create/': 'posts/post_create.html'
        }
        for address, template in url_templates_names.items():
            with self.subTest(address=address):
                response = self.authorized_client_author.get(address)
                self.assertTemplateUsed(response, template)
