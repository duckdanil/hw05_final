from django.test import TestCase, Client
from django.urls import reverse
from http import HTTPStatus
from django.core.cache import cache

from ..models import Group, Post, User


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')

        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test_slug',
            description='Описание теста'
        )

        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group
        )

        cls.urls_templates_public = (
            ('/', 'posts/index.html'),
            (f'/group/{cls.group.slug}/', 'posts/group_list.html'),
            (f'/profile/{cls.user}/', 'posts/profile.html'),
            (f'/posts/{cls.post.id}/', 'posts/post_detail.html')
        )

        cls.urls_templates_not_public = (
            ('/create/', 'posts/create_post.html'),
            (f'/posts/{cls.post.id}/edit/', 'posts/create_post.html')
        )

        cls.urls_public = [
            '/',
            f'/group/{cls.group.slug}/',
            f'/profile/{cls.user}/',
            f'/posts/{cls.post.id}/',
        ]

        cls.urls_not_public = [
            '/create/',
            f'/posts/{cls.post.id}/edit/',
        ]

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostURLTests.user)
        self.another_user = User.objects.create_user(username='user_logined')
        self.user_logined = Client()
        self.user_logined.force_login(self.another_user)
        cache.clear()

    def test_unauthorized_user_urls_status_code_public(self):
        """Проверка статуса публичных для неавторизованного пользователя."""
        for url in self.urls_public:
            with self.subTest(url=url):
                status_code = self.guest_client.get(url).status_code
                self.assertEqual(status_code, HTTPStatus.OK)

    def test_unauthorized_user_urls_status_code_not_public(self):
        """Проверка статуса непубличных для неавторизованного пользователя."""
        for url in self.urls_not_public:
            with self.subTest(url=url):
                status_code = self.guest_client.get(url).status_code
                self.assertEqual(status_code, HTTPStatus.FOUND)

    def test_authorized_user_urls_status_code_public(self):
        """Проверка статуса публичных для авторизованного пользователя."""
        for url in self.urls_public:
            with self.subTest(url=url):
                status_code = self.authorized_client.get(url).status_code
                self.assertEqual(status_code, HTTPStatus.OK)

    def test_authorized_user_urls_status_code_not_public(self):
        """Проверка статуса непубличных для авторизованного пользователя."""
        for url in self.urls_not_public:
            with self.subTest(url=url):
                status_code = self.authorized_client.get(url).status_code
                self.assertEqual(status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template_authorized_client(self):
        """URL-адрес использует соответствующий шаблон"""
        public = self.urls_templates_public
        not_public = self.urls_templates_not_public
        for url, template in public + not_public:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_redirect_client_on_login(self):
        """Страница post_edit перенаправит обычного пользователя
        на страницу поста.
        """
        response = self.user_logined.get(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.id}
            )
        )
        url = reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id}
        )
        self.assertRedirects(response, url)

    def test_url_returns_404(self):
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
