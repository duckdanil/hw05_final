from http import HTTPStatus

from django.contrib.auth import get_user
from django.core.cache import cache
from django.test import TestCase, Client
from django.urls import reverse

from ..models import Group, Post, User

INDEX = reverse('posts:index')
FOLLOW = reverse('posts:follow_index')
FOLLOW_USER = reverse('posts:profile_follow', args=['auth'])
UNFOLLOW_USER = reverse('posts:profile_unfollow', args=['auth'])
POST_CREATE = reverse('posts:post_create')
GROUP_LIST = reverse('posts:group_list', args=['test_slug'])
PROFILE = reverse('posts:profile', args=['auth'])
REDIRECT_LOGIN_POST_CREATE = reverse('users:login') + '?next=' + POST_CREATE
REDIRECT_LOGIN_FOLLOW = reverse('users:login') + '?next=' + FOLLOW_USER
REDIRECT_LOGIN_UNFOLLOW = reverse('users:login') + '?next=' + UNFOLLOW_USER
REDIRECT_LOGIN_FOLLOW_INDEX = reverse('users:login') + '?next=' + FOLLOW
UNEXISTING_PAGE = '/unexisting_page/'


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user_2 = User.objects.create_user(username='auth_2')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test_slug',
            description='Описание'
        )

        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group
        )
        cls.POST_DETAIL = reverse('posts:post_detail', args=[cls.post.id])
        cls.POST_EDIT = reverse('posts:post_edit', args=[cls.post.id])
        cls.REDIRECT_LOGIN_POST_EDIT = reverse(
            'users:login') + '?next=' + cls.POST_EDIT
        cls.author = Client()
        cls.author.force_login(cls.user)
        cls.another_user = Client()
        cls.another_user.force_login(cls.user_2)

    def test_urls_at_desired_location(self):
        """Проверяется доступность страниц с разными правами доступа."""
        pages_response = [
            [INDEX, self.client, HTTPStatus.OK],
            [GROUP_LIST, self.client, HTTPStatus.OK],
            [PROFILE, self.client, HTTPStatus.OK],
            [self.POST_DETAIL, self.client, HTTPStatus.OK],
            [self.POST_EDIT, self.client, HTTPStatus.FOUND],
            [POST_CREATE, self.client, HTTPStatus.FOUND],
            [UNEXISTING_PAGE, self.client, HTTPStatus.NOT_FOUND],
            [self.POST_EDIT, self.author, HTTPStatus.OK],
            [POST_CREATE, self.author, HTTPStatus.OK],
            [self.POST_EDIT, self.another_user, HTTPStatus.FOUND],
            [FOLLOW, self.client, HTTPStatus.FOUND],
            [FOLLOW, self.author, HTTPStatus.OK],
            [FOLLOW_USER, self.client, HTTPStatus.FOUND],
            [FOLLOW_USER, self.another_user, HTTPStatus.FOUND],
            [FOLLOW_USER, self.author, HTTPStatus.FOUND],
            [UNFOLLOW_USER, self.client, HTTPStatus.FOUND],
            [UNFOLLOW_USER, self.another_user, HTTPStatus.FOUND],
            [UNFOLLOW_USER, self.author, HTTPStatus.NOT_FOUND],
        ]
        for url, client, http in pages_response:
            with self.subTest(url=url, client=get_user(client).username):
                self.assertEqual(client.get(url).status_code, http)

    def test_anonymous_is_redirected_to_page(self):
        """Перенаправление пользователей с разными правамии доступа."""
        pages_redirect = [
            [POST_CREATE, self.client, REDIRECT_LOGIN_POST_CREATE],
            [self.POST_EDIT, self.client, self.REDIRECT_LOGIN_POST_EDIT],
            [self.POST_EDIT, self.another_user, self.POST_DETAIL],
            [FOLLOW_USER, self.client, REDIRECT_LOGIN_FOLLOW],
            [UNFOLLOW_USER, self.client, REDIRECT_LOGIN_UNFOLLOW],
            [FOLLOW, self.client, REDIRECT_LOGIN_FOLLOW_INDEX],
            [FOLLOW_USER, self.another_user, PROFILE],
            [UNFOLLOW_USER, self.another_user, PROFILE],
            [FOLLOW_USER, self.author, PROFILE],
        ]
        for url, client, redirect in pages_redirect:
            with self.subTest(url=url, client=get_user(client).username):
                self.assertRedirects(client.get(url), redirect)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        cache.clear()
        templates_url_names = {
            INDEX: 'posts/index.html',
            GROUP_LIST: 'posts/group_list.html',
            PROFILE: 'posts/profile.html',
            self.POST_DETAIL: 'posts/post_detail.html',
            self.POST_EDIT: 'posts/create_post.html',
            POST_CREATE: 'posts/create_post.html',
            FOLLOW: 'posts/follow.html',
            UNEXISTING_PAGE: 'core/404.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                self.assertTemplateUsed(
                    self.author.get(address),
                    template)
