import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django import forms


from ..models import Post, Group, User, Comment

TEST_USERNAME = 'test_username'
TEST_USERNAME_2 = 'test_username_2'
TEST_SLUG = 'test_slug'
TEST_SLUG_2 = 'test_slug_2'
LOGIN = reverse('users:login')
NEXT = '?next='
INDEX = reverse('posts:index')
POST_CREATE = reverse('posts:post_create')
GROUP_LIST = reverse('posts:group_list', args=[TEST_SLUG])
GROUP_LIST_2 = reverse('posts:group_list', args=[TEST_SLUG_2])
PROFILE = reverse('posts:profile', args=[TEST_USERNAME])
REDIRECT_LOGIN_POST_CREATE = f'{LOGIN}{NEXT}{POST_CREATE}'
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
TEST_IMAGE_2 = SimpleUploadedFile(
    name='test_img_2.png',
    content=IMAGE,
    content_type='image/png',
)
IMAGE_FOLDER = Post._meta.get_field("image").upload_to


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=TEST_USERNAME)
        cls.user_2 = User.objects.create_user(username=TEST_USERNAME_2)
        cls.group = Group.objects.create(
            slug=TEST_SLUG,
            title='Тестовый заголовок',
            description='Описание',
        )
        cls.group_2 = Group.objects.create(
            slug=TEST_SLUG_2,
            title='Тестовый заголовок_2',
            description='Описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовый пост',
        )
        cls.POST_DETAIL = reverse('posts:post_detail', args=[cls.post.id])
        cls.POST_EDIT = reverse('posts:post_edit', args=[cls.post.id])
        cls.COMMENT = reverse('posts:add_comment', args=[cls.post.id])
        cls.REDIRECT_POST_COMMENT = f'{LOGIN}{NEXT}{cls.COMMENT}'
        cls.REDIRECT_POST_EDIT = f'{LOGIN}{NEXT}{cls.POST_EDIT}'
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.authorized_client_2 = Client()
        cls.authorized_client_2.force_login(cls.user_2)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        """Валидная форма создает запись в БД."""
        Post.objects.all().delete()
        form_data = {
            'text': 'Тестовый пост_2',
            'group': self.group.id,
            'image': TEST_IMAGE,
        }
        response = self.authorized_client.post(
            POST_CREATE,
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, PROFILE)
        self.assertEqual(len(Post.objects.all()), 1)
        post = Post.objects.get()
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group_id, form_data['group'])
        self.assertEqual(post.author, self.user)
        self.assertEqual(
            post.image.name,
            f'{IMAGE_FOLDER}{form_data["image"].name}'
        )

    def test_edit_post(self):
        """Валидная форма редактирует запись в БД."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Пост с изменениями',
            'group': self.group_2.id,
            'image': TEST_IMAGE_2,
        }
        response = self.authorized_client.post(
            self.POST_EDIT,
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, self.POST_DETAIL)
        self.assertEqual(Post.objects.count(), posts_count)
        post = response.context['post']
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group_id, form_data['group'])
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(
            post.image.name,
            f'{IMAGE_FOLDER}{form_data["image"].name}'
        )

    def test_create_post_page_show_correct_context(self):
        """Шаблон create_post для создания и редактирования поста сформирован
        с правильным контекстом."""
        urls = (self.POST_EDIT, POST_CREATE)
        form_fields = {
            'text': forms.CharField,
            'group': forms.fields.ChoiceField,
        }
        for url in urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                for value, expected in form_fields.items():
                    form_field = response.context['form'].fields.get(value)
                    self.assertIsInstance(form_field, expected)

    def test_create_comment(self):
        """Комментарий создается в БД."""
        Comment.objects.all().delete()
        form_data = {'text': 'Тестовый комментарий'}
        response = self.authorized_client.post(
            self.COMMENT,
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, self.POST_DETAIL)
        self.assertEqual(len(Comment.objects.all()), 1)
        comment = Comment.objects.get()
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.post, self.post)
        self.assertEqual(comment.text, form_data['text'])

    def test_guest_cant_create_post_or_comment(self):
        """Неавторизованный пользователь не может создать
        пост или комментарий."""
        Post.objects.all().delete()
        Comment.objects.all().delete()
        model_address_data = (
            (Post, POST_CREATE, REDIRECT_LOGIN_POST_CREATE, {
                'text': 'Тестовый пост_2',
                'group': self.group_2.id,
                'image': TEST_IMAGE
            }),
            (Comment, self.COMMENT, self.REDIRECT_POST_COMMENT, {
                'text': 'Тестовый комментарий_2'
            }),
        )
        for obj, url, redirect_url, form_data, in model_address_data:
            with self.subTest(url=url):
                response = self.client.post(
                    url,
                    data=form_data,
                    follow=True
                )
                self.assertRedirects(response, redirect_url)
                self.assertEqual(len(obj.objects.all()), 0)

    def test_guest_and_no_author_cant_edit_post(self):
        """Неавторизованный пользователь и не-автор поста не может
        отредактировать пост."""
        client_text_address = (
            (self.client,
             'Пост измененный неавторизованным пользователем',
             self.REDIRECT_POST_EDIT),
            (self.authorized_client_2,
             'Пост измененный не автором',
             self.POST_DETAIL),
        )
        for client, text, redirect_url in client_text_address:
            with self.subTest(client=client):
                form_data = {
                    'text': text,
                    'group': self.group_2,
                    'image': TEST_IMAGE,
                }
                response = client.post(
                    self.POST_EDIT,
                    data=form_data,
                )
                post = Post.objects.get(id=self.post.id)
                self.assertRedirects(response, redirect_url)
                self.assertEqual(post.text, self.post.text)
                self.assertEqual(post.group, self.post.group)
                self.assertEqual(post.author, self.post.author)
                self.assertEqual(post.image, self.post.image)
