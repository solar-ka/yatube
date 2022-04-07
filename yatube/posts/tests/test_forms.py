import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import get_object_or_404
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class CommentCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def tearDown(self):
        cache.clear()

    def test_create_comment(self):
        """Валидная форма создает комментарий к посту."""
        form_data = {
            'text': 'текст комментария',
        }
        comments_count = Comment.objects.count()
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={
                'post_id': self.post.id
            }),
            data=form_data,
            follow=True
        )
        last_comment_in_database = Comment.objects.latest('created')
        self.assertRedirects(response, reverse('posts:post_detail', kwargs={
            'post_id': self.post.id
        }))
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertEqual(last_comment_in_database.text, form_data['text'])


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.group_1 = Group.objects.create(
            title='Тестовая группа 1',
            slug='test-slug1',
            description='Тестовое описание 1',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
        )
        cls.post_in_group = Post.objects.create(
            text='Тестовый текст в группе',
            author=cls.author,
            group=cls.group_1
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def tearDown(self):
        cache.clear()

    def create_post_test_helper(self, form_data):
        """Вспомогательная функция для проверки создания поста."""
        posts_count = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        last_post = Post.objects.latest('pub_date')
        self.assertRedirects(response, reverse('posts:profile', kwargs={
            'username': self.author.username
        }))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(last_post.text, form_data['text'])

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        form_data = {
            'text': 'текст 3',
        }
        self.create_post_test_helper(form_data)

    def test_create_post_with_group(self):
        """Валидная форма с группой создает запись в Post."""
        form_data = {
            'text': 'текст 4',
            'group': self.group_1.id,
        }
        self.create_post_test_helper(form_data)
        self.assertEqual(
            Post.objects.latest('pub_date').group.id, form_data.get('group'))

    def test_create_post_with_image(self):
        """Валидная форма с картинкой создаёт запись в Post."""
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
        form_data = {
            'text': 'текст с картинкой',
            'group': self.group_1.id,
            'image': uploaded,
        }
        self.create_post_test_helper(form_data)
        self.assertEqual(
            Post.objects.latest('pub_date').image, 'posts/small.gif'
        )

    def edit_post_test_helper(self, form_data):
        """Вспомогательная функция для проверки редактирования поста."""
        posts_count = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse('posts:post_detail', kwargs={
            'post_id': self.post.id
        }))
        self.assertEqual(Post.objects.count(), posts_count)

        self.assertEqual(
            get_object_or_404(Post, id=self.post.id).text,
            form_data.get('text')
        )

    def test_edit_post(self):
        """Изменение поста работает корректно."""
        form_data = {
            'text': 'текст 5',
        }
        self.edit_post_test_helper(form_data)

    def test_edit_post_with_group(self):
        """Изменение поста с группой работает корректно."""
        form_data = {
            'text': 'текст 5',
            'group': self.group_1.id
        }
        self.edit_post_test_helper(form_data)
        self.assertEqual(
            get_object_or_404(Post, id=self.post.id).group.id,
            form_data.get('group')
        )
