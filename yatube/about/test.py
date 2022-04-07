from http import HTTPStatus

from django.test import Client, TestCase


class StaticURLTests(TestCase):
    def setUp(self):
        # Создаём экземпляр клиента. Он неавторизован.
        self.guest_client = Client()

    def test_about_exists(self):
        """Доступность about для неавторизованного пользователя."""
        url_responses_code = {
            '/about/author/': HTTPStatus.OK,
            '/about/tech/': HTTPStatus.OK
        }
        for address, code in url_responses_code.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, code)

    def test_about_uses_correct_template(self):
        """URL-адрес about использует соответствующий шаблон."""
        # Шаблоны по адресам
        url_templates_names = {
            '/about/author/': 'about/author.html',
            '/about/tech/': 'about/tech.html',
        }
        for address, template in url_templates_names.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertTemplateUsed(response, template)
