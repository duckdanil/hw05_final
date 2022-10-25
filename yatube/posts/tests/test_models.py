from django.test import TestCase

from ..models import Group, Post, User, Comment, Follow


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user2 = User.objects.create_user(username='auth2')
        cls.follow = Follow.objects.create(
            user=cls.user,
            author=cls.user2,
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост больше 15 символов',
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовый описание'
        )
        cls.comment = Comment.objects.create(
            text='Тестовый комментарий больше 15 символов',
            author=cls.user,
            post=cls.post,
        )

    def test_models_str_post_(self):
        """Проверяем, что корректно работает __str__ у post """
        self.assertEqual(self.post.text[:15], str(self.post))

    def test_models_str_group(self):
        """Проверяем, что корректно работает __str__ у group."""
        self.assertEqual(self.group.title, str(self.group))

    def test_models_str_comment(self):
        """Проверка, что корректно работает __str__ у сomment."""
        self.assertEqual(self.comment.text[:15], str(self.comment))

    def test_models_str_follow(self):
        """Проверка, что корректно работает __str__ у follow."""
        self.assertEqual(
            f'{self.follow.user.username}'
            f' подписался на {self.follow.author.username}',
            str(self.follow))

    def test_post_verbose_name(self):
        """Проверка verbose_name у post."""
        field_verboses = {
            'text': 'Текст',
            'pub_date': 'Дата публикации',
            'author': 'Автор',
            'group': 'Группа',
        }
        for value, expected in field_verboses.items():
            with self.subTest(value=value):
                verbose_name = Post._meta.get_field(value).verbose_name
                self.assertEqual(verbose_name, expected)

    def test_group_verbose_name(self):
        """Проверка verbose_name у group."""
        field_verboses = {
            'title': 'Заголовок',
            'description': 'Описание'
        }
        for value, expected in field_verboses.items():
            with self.subTest(value=value):
                verbose_name = Group._meta.get_field(value).verbose_name
                self.assertEqual(verbose_name, expected)

    def test_comment_verbose_name(self):
        """Проверка verbose_name у comment."""
        field_verboses = {
            'post': 'Пост',
            'created': 'Дата создания',
            'author': 'Автор',
            'text': 'Текст',
        }
        for value, expected in field_verboses.items():
            with self.subTest(value=value):
                verbose_name = Comment._meta.get_field(value).verbose_name
                self.assertEqual(verbose_name, expected)

    def test_follow_verbose_name(self):
        """Проверка verbose_name у follow."""
        field_verboses = {
            'user': 'Пользователь',
            'author': 'Автор',
        }
        for value, expected in field_verboses.items():
            with self.subTest(value=value):
                verbose_name = Follow._meta.get_field(value).verbose_name
                self.assertEqual(verbose_name, expected)
