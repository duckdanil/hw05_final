from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import UniqueConstraint

User = get_user_model()


class Group(models.Model):
    title = models.CharField(
        max_length=200,
        verbose_name='Заголовок'
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name='Строка идентификатор'
    )
    description = models.TextField(
        max_length=400,
        verbose_name='Описание'
    )

    class Meta:
        verbose_name_plural = 'Группы'
        verbose_name = 'Группу'

    def __str__(self):
        return self.title


class Post(models.Model):
    text = models.TextField(
        verbose_name='Текст',
        help_text='Текст поста'
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата публикации'
    )
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='posts'
    )
    group = models.ForeignKey(
        Group,
        verbose_name='Группа',
        help_text='Группа, к которой относится пост',
        on_delete=models.SET_NULL,
        related_name="posts",
        blank=True,
        null=True
    )
    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True
    )

    def __str__(self):
        return self.text[:15]

    class Meta:
        ordering = ['-pub_date']
        verbose_name_plural = 'Посты'
        verbose_name = 'Пост'


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Пост')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Автор')
    text = models.TextField(
        verbose_name='Текст')
    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания')

    class Meta:
        ordering = ['-created']
        verbose_name_plural = 'Коментарии'
        verbose_name = 'Коментарий'

    def __str__(self):
        return self.text[:15]    


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Пользователь')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор')

    class Meta:
        verbose_name_plural = 'Подписки'
        verbose_name = 'Подписка'
        constraints = [
            UniqueConstraint(fields=['author', 'user'], name='unique_follow')
        ]

    def __str__(self):
        return f'{self.user} подписался на {self.author}'    
