from django.template.defaultfilters import slugify
from django.contrib.auth import get_user_model
from django.utils.safestring import mark_safe
from django.db.models import Count
from transliterate import translit
from django.urls import reverse
from datetime import datetime
from django.db import models

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
        on_delete=models.CASCADE,
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
        to=User,
        verbose_name='Пользователь',
        related_name='users'
    )
    creator = models.ForeignKey(
        to=User,
        verbose_name='Создатель',
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
        return f'{self.name.__str__()} - {self.creator.__str__()}'

    def get_absolute_url(self, name_path='tree'):
        return reverse(name_path, kwargs={'tree': self.slug})

    def get_count_human(self):
        number = Human.objects.filter(tree=self).count()
        word = get_declination_from_numeral(number, 'имя', 'имени', 'имён')
        return f'{number} {word}'

    def get_count_users(self):
        number = self.user.count() - 1
        if number == 0:
            return 'в гордом одиночестве'
        word = get_declination_from_numeral(number, 'и ещё {} человек', 'и ещё {} человека', 'и ещё {} человек')
        return word.format(number)

    def get_journal_url(self):
        return reverse('journal_tree', kwargs={'tree': self.slug})


class Message(models.Model):
    text = models.TextField(
        verbose_name='Содержание'
    )
    sender = models.ForeignKey(
        verbose_name='Отправитель',
        to=User,
        related_name='sender',
        on_delete=models.CASCADE
    )
    recipient = models.ForeignKey(
        verbose_name='Получатель',
        to=User,
        related_name='recipient',
        on_delete=models.CASCADE
    )
    sending_time = models.DateTimeField(
        verbose_name='Время отправки',
        default=datetime.now()
    )
    check_read_it = models.BooleanField(
        verbose_name='Прочитано',
        default=False
    )
    text_for_sender = models.TextField(
        verbose_name='Текст сообщения для отправляющего',
        default=''
    )

    @staticmethod
    def get_number_unread_messages(user):
        return len(Message.objects.filter(recipient=user, check_read_it=False))

    def get_mark_safe_text(self):
        return mark_safe(self.text)

    def get_mark_safe_text_for_sender(self):
        return mark_safe(self.text_for_sender)

    def __str__(self):
        return f'{self.sending_time}: {self.sender.first_name} {self.sender.last_name} -> {self.recipient.first_name} {self.recipient.last_name}'


def get_declination_from_numeral(number, one, two, five):
    last_figure = number % 10
    return five if last_figure > 4 or 4 < number < 15 or last_figure == 0 else two if last_figure != 1 else one


class NumberChanges(models.Model):
    user = models.ForeignKey(
        verbose_name='Пользователь',
        to=User,
        on_delete=models.CASCADE,
        related_name='user'
    )
    tree = models.ForeignKey(
        verbose_name='Дерево',
        to=Tree,
        on_delete=models.CASCADE,
        related_name='tree'
    )
    number = models.IntegerField(
        verbose_name='Количество изменений'
    )

    def __str__(self):
        return f'{self.user} {self.tree.name} {self.number}'
