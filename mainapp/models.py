from django.db import models
from django.template.defaultfilters import slugify
from transliterate import translit
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class Human(models.Model):
    tree = models.ForeignKey(
        'Tree',
        verbose_name='Дерево',
        on_delete=models.CASCADE
    )
    first_name = models.CharField(
        max_length=255,
        verbose_name='Имя',
        null=True,
        blank=True
    )
    last_name = models.CharField(
        max_length=255,
        verbose_name='Фамилия',
        null=True,
        blank=True
    )
    image = models.ImageField(
        null=True,
        blank=True,
        verbose_name='Изображение',
        upload_to='human_face'
    )
    slug = models.SlugField(
        default=None,
        null=True,
        blank=True
    )
    parent = models.ForeignKey(
        'Human',
        null=True,
        blank=True,
        verbose_name='Родитель',
        on_delete=models.SET_NULL,
        related_name='related_children'
    )

    def save(self, *args, **kwargs):
        slug = translit(
                self.parent.first_name.__str__() + '_' + self.__str__() if self.parent else self.__str__(),
                'ru',
                reversed=True
            )
        self.slug = slugify(slug)
        super().save(*args, **kwargs)

    def __str__(self):
        if not self.last_name.__str__() == 'None':
            return "{} {}".format(
                self.first_name.__str__(),
                self.last_name.__str__()
            )
        else:
            return self.first_name.__str__()

    def get_absolute_url(self, name_path='human_detail'):
        return reverse(name_path, kwargs={
            'slug': self.slug,
            'tree': self.tree.slug
        })


class Tree(models.Model):
    name = models.CharField(
        max_length=255,
        verbose_name='Название'
    )
    user = models.ManyToManyField(
        User,
        verbose_name='Пользователь',
        related_name='users'
    )
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='creator'
    )
    slug = models.SlugField(
        default=None,
        null=True,
        blank=True,
        unique=True
    )

    def save(self, *args, **kwargs):
        self.slug = slugify(translit(
            self.name.__str__() + '_' + self.creator.username.__str__(),
            'ru',
            reversed=True)
        )
        super().save(*args, **kwargs)
        if self.user.all().count() == 0:
            self.user.add(self.creator)
            super().save(*args, **kwargs)

    def __str__(self):
        return self.name.__str__()

    def get_absolute_url(self, name_path='tree'):
        return reverse(name_path, kwargs={'tree': self.slug})
