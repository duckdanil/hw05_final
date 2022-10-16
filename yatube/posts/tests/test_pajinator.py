from django.test import Client, TestCase

from ..models import Group, Post, User

POSTS_ON_FIRST_PAGE = 10
POSTS_ON_SECOND_PAGE = 3
COUNT_POSTS = POSTS_ON_FIRST_PAGE + POSTS_ON_SECOND_PAGE


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.authorized_client = Client()
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание'
        )
        Post.objects.bulk_create([
            Post(author=cls.user, text='Тестовый пост', group=cls.group)
            for _ in range(COUNT_POSTS)
        ])
        cls.paginator_urls = [
            '/',
            f'/group/{cls.group.slug}/',
            f'/profile/{cls.user}/'
        ]

    def test_pajinator(self):

        pages = (
            (1, POSTS_ON_FIRST_PAGE),
            (2, POSTS_ON_SECOND_PAGE)
        )
        for page, count in pages:
            for url in self.paginator_urls:
                with self.subTest(url=url):
                    response = self.client.get(url, {"page": page})
                    self.assertEqual(
                        len(response.context["page_obj"].object_list), count
                    )
