from django import forms
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, User, Follow


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание группы',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded
        )
        cls.INDEX = reverse(
            'posts:index'
        )
        cls.GROUP_LIST = reverse(
            'posts:group_list', kwargs={'slug': 'test-slug'}
        )
        cls.PROFILE = reverse(
            'posts:profile', kwargs={'username': 'auth'}
        )
        cls.POST_DETAIL = reverse(
            'posts:post_detail', kwargs={'post_id': cls.post.id}
        )
        cls.POST_CREATE = reverse(
            'posts:post_create'
        )
        cls.POST_EDIT = reverse(
            'posts:post_edit', kwargs={'post_id': PostPagesTests.post.id}
        )
        cls.public_urls = (
            (PostPagesTests.INDEX, 'posts/index.html'),
            (PostPagesTests.GROUP_LIST, 'posts/group_list.html'),
            (PostPagesTests.PROFILE, 'posts/profile.html'),
            (PostPagesTests.POST_DETAIL, 'posts/post_detail.html')
        )
        cls.not_public_urls = (
            (PostPagesTests.POST_CREATE, 'posts/create_post.html'),
            (PostPagesTests.POST_EDIT, 'posts/create_post.html')
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for reverse_name, template in self.public_urls + self.not_public_urls:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def check_fields(self, post):
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.group, self.group)
        self.assertEqual(post.image, self.post.image)

    def test_correct_template(self):
        """Шаблоны публичные сформированы с правильным контекстом."""
        for reverse_name, template in self.public_urls:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)
                if 'page_obj' in response.context:
                    post = response.context.get('page_obj')[0]
                else:
                    post = response.context.get('post')
                self.check_fields(post)

    def test_not_public_context(self):
        """Шаблоны непубличные сформированы с правильным контекстом"""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.ChoiceField,
            'image': forms.fields.ImageField
        }
        for reverse_name, _ in self.not_public_urls:
            for field_name, expected in form_fields.items():
                with self.subTest(
                        reverse_name=reverse_name, field_name=field_name):
                    response = self.authorized_client.get(reverse_name)
                    form_field = response.context.get(
                        'form'
                    ).fields.get(field_name)
                    self.assertIsInstance(form_field, expected)

    def test_forms_show_correct(self):
        """Проверка коректности формы."""
        context = {
            self.POST_CREATE,
            self.POST_EDIT,
        }
        for reverse_page in context:
            with self.subTest(reverse_page=reverse_page):
                response = self.authorized_client.get(reverse_page)
                self.assertIsInstance(
                    response.context['form'].fields['text'],
                    forms.fields.CharField)
                self.assertIsInstance(
                    response.context['form'].fields['group'],
                    forms.fields.ChoiceField)
                self.assertIsInstance(
                    response.context['form'].fields['image'],
                    forms.fields.ImageField)

    def test_cache_index(self):
        response = self.authorized_client.get(reverse('posts:index'))
        resp_1 = response.content
        self.post2 = Post.objects.create(
            text='Тестовый пост 2',
            author=self.user,
            group=self.group
        )
        response_2 = self.authorized_client.get(reverse('posts:index'))
        resp_2 = response_2.content
        self.assertTrue(resp_1 == resp_2)
        cache.clear()
        response_3 = self.authorized_client.get(reverse('posts:index'))
        resp_3 = response_3.content
        self.assertTrue(resp_2 != resp_3)


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_autor = User.objects.create(
            username='post_autor',
        )
        cls.post_follower = User.objects.create(
            username='post_follower',
        )
        cls.post = Post.objects.create(
            text='Подпишись на меня',
            author=cls.post_autor,
        )
        cls.FOLLOW_INDEX = reverse(
            'posts:follow_index'
        )
        cls.PROFILE_UNFOLLOW = reverse(
            'posts:profile_unfollow',
            kwargs={'username': cls.post_follower}
        )
        cls.PROFILE_FOLLOW = reverse(
            'posts:profile_follow',
            kwargs={'username': cls.post_follower}
        )

    def setUp(self):
        cache.clear()
        self.author_client = Client()
        self.author_client.force_login(self.post_follower)
        self.follower_client = Client()
        self.follower_client.force_login(self.post_autor)

    def test_follow_on_user(self):
        """Проверка подписки на пользователя."""
        count_follow = Follow.objects.count()
        self.follower_client.post(
            FollowViewsTest.PROFILE_FOLLOW)
        follow = Follow.objects.all().latest('id')
        self.assertEqual(Follow.objects.count(), count_follow + 1)
        self.assertEqual(follow.author_id, self.post_follower.id)
        self.assertEqual(follow.user_id, self.post_autor.id)

    def test_unfollow_on_user(self):
        """Проверка отписки от пользователя."""
        Follow.objects.create(
            user=self.post_autor,
            author=self.post_follower)
        count_follow = Follow.objects.count()
        self.follower_client.post(FollowViewsTest.PROFILE_UNFOLLOW)
        self.assertEqual(Follow.objects.count(), count_follow - 1)

    def test_follow_on_authors(self):
        """Проверка записей у тех кто подписан."""
        post = Post.objects.create(
            author=self.post_autor,
            text="Подпишись на меня")
        Follow.objects.create(
            user=self.post_follower,
            author=self.post_autor)
        response = self.author_client.get(FollowViewsTest.FOLLOW_INDEX)
        self.assertIn(post, response.context['page_obj'].object_list)

    def test_notfollow_on_authors(self):
        """Проверка записей у тех кто не подписан."""
        post = Post.objects.create(
            author=self.post_autor,
            text="Подпишись на меня")
        response = self.author_client.get(FollowViewsTest.FOLLOW_INDEX)
        self.assertNotIn(post, response.context['page_obj'].object_list)
