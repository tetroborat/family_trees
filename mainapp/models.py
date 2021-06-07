from django.template.defaultfilters import slugify
from django.contrib.auth import get_user_model
from django.utils.safestring import mark_safe
from transliterate import translit
from django.urls import reverse
from django.db import models

User = get_user_model()


class Human(models.Model):
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
        blank=True,
        verbose_name='Создаётся авт-ки'
    )
    parents = models.ManyToManyField(
        to='Human',
        verbose_name='Родители',
        blank=True
    )
    user = models.OneToOneField(
        to=User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='Пользователь (если есть)'
    )
    date_of_birth = models.DateField(
        verbose_name='Дата рождения',
        null=True
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        slug = translit(
                f'{self.pk}_{self.__str__()}',
                'ru',
                reversed=True
            )
        self.slug = slugify(slug)
        super().save(*args, **kwargs)

    def __str__(self):
        if self.last_name.__str__() == 'None':
            return self.first_name.__str__()
        else:
            return f'{self.first_name.__str__()} {self.last_name.__str__()}'

    def get_absolute_url(self, name_path='human_detail'):
        return reverse(name_path, kwargs={
            'slug': self.slug
        })


class Tree(models.Model):
    humans = models.ManyToManyField(
        to=Human,
        verbose_name='Люди',
        related_name='trees'
    )
    user = models.ManyToManyField(
        to=User,
        verbose_name='Пользователь',
        related_name='trees'
    )
    potential_user = models.ManyToManyField(
        to=User,
        verbose_name='Ожидающие разрешения',
        related_name='potential_trees',
        null=True,
        blank=True
    )
    oldest_human = models.OneToOneField(
        to=Human,
        verbose_name='Прародитель',
        null=True,
        on_delete=models.SET_NULL,
        related_name='oldest_human'
    )
    creator = models.ForeignKey(
        to=User,
        verbose_name='Создатель',
        null=True,
        on_delete=models.SET_NULL,
        related_name='creator'
    )
    slug = models.SlugField(
        default=None,
        null=True,
        blank=True,
        unique=True,
        verbose_name='Слаг (создаётся авт-ки)'
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.slug = slugify(translit(
            f'{self.pk}_descendants_of_{self.__str__()}',
            'ru',
            reversed=True)
        )
        print(self.user.first(), self.user.count())
        if self.user.count() == 1:
            self.creator = self.user.first()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.oldest_human.__str__()

    def get_absolute_url(self, name_path='tree'):
        return reverse(name_path, kwargs={'tree': self.slug})

    def get_count_human(self):
        number = self.humans.all().count() - 1
        word = get_declination_from_numeral(number, 'потомок', 'потомка', 'потомков')
        return f'{number} {word}' if number > 0 else ''

    def get_count_users(self):
        number = self.user.count() - 1
        if number == 0:
            return 'в гордом одиночестве'
        word = get_declination_from_numeral(number, 'и ещё {} человек', 'и ещё {} человека', 'и ещё {} человек')
        return word.format(number) if number > 0 else ''

    def get_journal_url(self):
        return reverse('journal_tree', kwargs={'tree': self.slug})

    def get_short_name(self):
        return self.oldest_human.first_name[0] + self.oldest_human.last_name[0] if self.oldest_human.last_name else self.oldest_human.first_name[0]


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
        verbose_name='Время отправки'
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
        return f'{self.sending_time.strftime("%H:%M %d.%m.%Y")}:  {self.sender.first_name} {self.sender.last_name} -> {self.recipient.first_name} {self.recipient.last_name}'


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
        return f'{self.user} {self.tree} {self.number}'
