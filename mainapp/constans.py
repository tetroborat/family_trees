str_tree_delete = 'Дерево "{}" и его содержиоме удалено'
str_tree_input = 'Дерево "{}" добавлено'
str_human_delete_tree = '{} и его(её) потомки удалены из дерева {}'
str_human_input_tree = '{} добавлен(-а) в дерево {}'
str_human_update = 'Информация о человеке {} обновлена'
str_user_update = 'Информация о пользователе @{} обновлена'
str_user_delete = 'Аккаунт пользователя @{} удален'
str_user_input = 'Аккаунт @{} успешно зарегестрирован!'
str_user_accept_tree = 'Пользователь @{} допущен к дереву "{}"'
str_user_dontaccept_tree = 'Доступ @{} к дереву "{}" прекращен'

li_tree_with_image = '<li><div class="block_tree"><div class="around_photo_tree"><div class="photo_tree"><img class="personPhoto" src="{}"></div></div><div class="a_tree"><a href="{}">{}</a></div></div>'
li_tree = '<li><div class="block_tree"><div class="a_tree"><a class="without_image" href="{}">{}</a></div></div>'
li_breadcrumb = '<li class="breadcrumb-item"><a href="{}">{}</a></li>'
li_breadcrumb_without_href = '<lii class="breadcrumb-item active" aria-current="page">{}</lii>'

mes_permission = 'Пользователь запрашивает разрешение на доступ к дереву ' \
                 '<a href="{}"><span class="shadow badge rounded-pill bg-success text-dark">{}</span></a>' \
                 '<div class="row" style="margin: 0">' \
                 '<a class="btn btn-primary col" href="{}" style="padding: 5px; border-radius: 10px; margin: 15px 10px 0 0">Разрешить</a>' \
                 '<a class="btn btn-danger col" href="{}" style="padding: 5px; border-radius: 10px; margin: 15px 0 0 0">Отклонить</a>' \
                 '</div>'
mes_permission_for_sender = 'Вы запросили доступ к дереву <a href="{}">' \
                            '<span class="shadow badge rounded-pill bg-success text-dark">{}</span></a>'
mes_permission_success = 'Пользователь запрашивает разрешение на доступ к дереву ' \
                         '<a href="{}"><span class="shadow badge rounded-pill bg-success text-dark">{}</span></a><br>' \
                         '<small class="text-muted" style="padding-left: 3px">Доступ разрешен</small>'
mes_permission_for_sender_success = 'Вы запросили доступ к дереву <a href="{}">' \
                                    '<span class="shadow badge rounded-pill bg-success text-dark">{}</span></a><br>' \
                                    '<small class="text-muted" style="padding-left: 3px"><font color="#fbfbf5">Доступ разрешен</font></small>'
mes_permission_deviation = 'Пользователь запрашивает разрешение на доступ к дереву ' \
                         '<a href="{}"><span class="shadow badge rounded-pill bg-success text-dark">{}</span></a><br>' \
                         '<small class="text-muted" style="padding-left: 3px"><font color="red">Доступ отклонен</font></small>'
mes_permission_for_sender_deviation = 'Вы запросили доступ к дереву <a href="{}">' \
                                    '<span class="shadow badge rounded-pill bg-success text-dark">{}</span></a><br>' \
                                    '<small class="text-muted" style="padding-left: 3px"><font color="red">Доступ отклонен</font></small>'

immediate_family_dictionary = {
    'masc': {
        -2: 'внук',
        -1: 'сын',
        0: 'брат',
        1: 'папа',
        2: 'дедушка'
    },
    'femn': {
        -2: 'внучка',
        -1: 'дочь',
        0: 'сестра',
        1: 'мама',
        2: 'бабушка'
    }
}
kinship_range_dictionary = {
    2: 'Двоюродн',
    3: 'Троюродн',
    4: 'Четвёрородн',
    5: 'Пятерородн',
    6: 'Шестерородн',
    7: 'Семерородн',
    8: 'Восьмерородн',
    9: 'Девятерородн',
    10: 'Десятерородн'
}
generational_difference_dictionary = {
    'masc': {
        -2: 'внук',
        -1: 'племянник',
        0: 'брат',
        1: 'дядя',
        2: 'дедушка'
    },
    'femn': {
        -2: 'внучка',
        -1: 'племянница',
        0: 'сестра',
        1: 'тётя',
        2: 'бабушка'
    }
}
gender_end = {
    'femn': 'ая',
    'masc': 'ый'
}
who_i = {
    'masc': 'Сам себе друг',
    'femn': 'Самая понимающая подруга'
}
