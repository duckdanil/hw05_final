import shutil
import tempfile

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post, User, Follow

TEST_USERNAME = 'test_username'
TEST_USERNAME_2 = 'test_username_2'
TEST_SLUG = 'test_slug'
TEST_SLUG_2 = 'test_slug_2'
INDEX = reverse('posts:index')
POST_CREATE = reverse('posts:post_create')
GROUP_LIST = reverse('posts:group_list', args=[TEST_SLUG])
GROUP_LIST_2 = reverse('posts:group_list', args=[TEST_SLUG_2])
PROFILE = reverse('posts:profile', args=[TEST_USERNAME])
FOLLOW = reverse('posts:follow_index')
FOLLOW_USER = reverse('posts:profile_follow', args=[TEST_USERNAME_2])
UNFOLLOW_USER = reverse('posts:profile_unfollow', args=[TEST_USERNAME])
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
IMAGE = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)
TEST_IMAGE = SimpleUploadedFile(
    name='test_img.png',
    content=IMAGE,
    content_type='image/png',
)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=TEST_USERNAME)
        cls.user_2 = User.objects.create_user(username=TEST_USERNAME_2)
        Follow.objects.create(
            user=cls.user_2,
            author=cls.user
        )
        cls.group = Group.objects.create(
            slug=TEST_SLUG,
            title='Тестовая группа',
            description='Тестовое описание',
        )
        cls.group_2 = Group.objects.create(
            slug=TEST_SLUG_2,
            title='Тестовая группа_2',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовый пост',
            image=TEST_IMAGE
        )
        cls.POST_DETAIL = reverse('posts:post_detail', args=[cls.post.id])
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.authorized_client_2 = Client()
        cls.authorized_client_2.force_login(cls.user_2)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_correct_template_context(self):
        """Шаблоны сформированы с правильным контекстом."""
        cache.clear()
        template_cases = (
            (INDEX, self.authorized_client, 'page_obj'),
            (FOLLOW, self.authorized_client_2, 'page_obj'),
            (GROUP_LIST, self.authorized_client, 'page_obj'),
            (PROFILE, self.authorized_client, 'page_obj'),
            (self.POST_DETAIL, self.authorized_client, 'post'),
        )
        for url, client, obj in template_cases:
            with self.subTest(url=url):
                response = client.get(url)
                if obj == 'page_obj':
                    self.assertEqual(len(response.context[obj]), 1)
                    post = response.context[obj][0]
                elif obj == 'post':
                    post = response.context[obj]
                self.assertEqual(post.id, self.post.id)
                self.assertEqual(post.text, self.post.text)
                self.assertEqual(post.author, self.post.author)
                self.assertEqual(post.group, self.post.group)
                self.assertEqual(post.image, self.post.image)

    def test_post_not_appear_another_group_and_another_follow(self):
        """Пост не появляется в group_list и follow_index, для которых
        не предназначен."""
        urls = (GROUP_LIST_2, FOLLOW)
        for url in urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertNotIn(self.post, response.context['page_obj'])

    def test_author_profile_context(self):
        """Автор в контексте профиля."""
        response = self.authorized_client.get(PROFILE)
        author = response.context['author']
        self.assertEqual(author, self.user)

    def test_group_in_context_group_list(self):
        """Группа в контексте групп-ленты без искажения атрибутов."""
        response = self.authorized_client.get(GROUP_LIST)
        group = response.context['group']
        self.assertEqual(group.slug, self.group.slug)
        self.assertEqual(group.title, self.group.title)
        self.assertEqual(group.description, self.group.description)
        self.assertEqual(group.id, self.group.id)

    def test_paginator(self):
        """Тест работы паджинатора."""
        cache.clear()
        Post.objects.all().delete()
        self.posts = Post.objects.bulk_create(
            Post(
                author=self.user,
                group=self.group,
                text=f'Тестовый пост {i}',
            )
            for i in range(settings.POSTS_PER_PAGE + 3)
        )
        pages = [
            [INDEX, settings.POSTS_PER_PAGE],
            [GROUP_LIST, settings.POSTS_PER_PAGE],
            [PROFILE, settings.POSTS_PER_PAGE],
            [FOLLOW, settings.POSTS_PER_PAGE],
            [f'{INDEX}?page=2', 3],
            [f'{GROUP_LIST}?page=2', 3],
            [f'{PROFILE}?page=2', 3],
            [f'{FOLLOW}?page=2', 3],
        ]
        for page, posts in pages:
            with self.subTest(page=page):
                response = self.authorized_client_2.get(page)
                self.assertEqual(len(response.context['page_obj']), posts)

    def test_cache_index(self):
        """Проверка кэша на главной странице."""
        response_1 = self.authorized_client.get(INDEX)
        Post.objects.all().delete
        response_2 = self.authorized_client.get(INDEX)
        self.assertEqual(response_1.content, response_2.content)
        cache.clear()
        response_3 = self.authorized_client.get(INDEX)
        self.assertNotEqual(response_1.content, response_3.content)

    def test_user_follow(self):
        """Проверка подписки на пользователей."""
        follow_count = Follow.objects.count()
        self.authorized_client.get(FOLLOW_USER)
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        self.assertTrue(
            Follow.objects.filter(
                user=self.user,
                author=self.user_2
            ).exists()
        )

    def test_user_unfollow(self):
        """Проверка отписки от пользователей."""
        follow_count = Follow.objects.count()
        self.authorized_client_2.get(UNFOLLOW_USER)
        self.assertEqual(Follow.objects.count(), follow_count - 1)
        self.assertFalse(
            Follow.objects.filter(
                user=self.user_2,
                author=self.user
            ).exists()
        )
