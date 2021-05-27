from django.http import HttpResponseRedirect, JsonResponse
from django.contrib.auth import authenticate, login
from django.contrib import messages
from pymorphy2 import MorphAnalyzer
from fuzzywuzzy import process
from datetime import datetime
from .constans import *
from .models import *


def get_tree(parent, humans):
    def get_str(p):
        if p.image:
            str_tree = li_tree_with_image.format(p.image.url, p.get_absolute_url('human_detail'), p)
        else:
            str_tree = li_tree.format(p.get_absolute_url('human_detail'), p)
        children = humans.filter(parents=p).order_by('date_of_birth')
        if children:
            str_tree += '<ul>'
            for child in children:
                str_tree += get_str(child)
            str_tree += '</ul>'
        return str_tree

    return '<ul>' + get_str(parent) + '</ul>'


def get_absolute_url_user(user, name_path='user_info'):
    return reverse(name_path, kwargs={'username': user.username})


def authenticate_user(request):
    if not User.objects.filter(username=request.POST.get('username')).exists():
        messages.error(request, 'Пользователя с таким логином не существует')
        return HttpResponseRedirect('/login/')
    user = authenticate(username=request.POST.get('username'), password=request.POST.get('password'))
    if user is not None:
        if user.is_active:
            login(request, user)
            return HttpResponseRedirect(reverse('user_info', kwargs={'username': user.username}))
        else:
            print("The password is valid, but the account has been disabled!")
    else:
        messages.error(request, 'Неверный пароль')
        return HttpResponseRedirect('/login/')


def get_queryset(request, query, accuracy=60, with_one_username=True):
    people = Human.objects.all()
    object_list = []
    search_human = process.extract(query, map(Human.__str__, people), limit=20)
    for human in search_human:
        if human[1] > accuracy:
            if len(human[0].split(' ')) > 1:
                f, l = human[0].split(' ')[0], human[0].split(' ')[1]
            else:
                f, l = human[0].split(' ')[0], None
            if with_one_username and request.user.first_name == f and request.user.last_name == l:
                user = people.filter(first_name=f, last_name=l).first()
                if user not in object_list:
                    object_list.append(user)
            else:
                found_humans = people.filter(first_name=f, last_name=l)
                for found_human in found_humans:
                    if found_human not in object_list:
                        object_list.append(found_human)
    return object_list


def get_users(query):
    users = User.objects.all()
    object_list = []
    search_users = process.extract(query, [f'{user.first_name} {user.last_name}' for user in users], limit=20)
    for human in search_users:
        if human[1] >= 90:
            if len(human[0].split(' ')) > 1:
                f, l = human[0].split(' ')[0], human[0].split(' ')[1]
            else:
                f, l = human[0].split(' ')[0], None
            found_humans = users.filter(first_name=f, last_name=l)
            for found_human in found_humans:
                if found_human not in object_list:
                    object_list.append(found_human)
    return object_list


def get_possible_trees(request):
    possible_trees = []
    queryset = get_queryset(
        request,
        f'{request.user.first_name} {request.user.last_name}',
        accuracy=90,
        with_one_username=False
    )
    tree = Tree.objects.all()
    for human in queryset:
        human_tree = tree.filter(humans=human)
        for item_tree in human_tree:
            if item_tree not in possible_trees:
                possible_trees.append(item_tree)
    return possible_trees


def get_last_messages_and_dialogs(user):
    all_user_messages = Message.objects.filter(sender=user) | Message.objects.filter(recipient=user)
    all_user_messages = all_user_messages.order_by('-sending_time')
    last_messages = {}
    interlocutors = []
    for message in all_user_messages:
        sender = message.sender
        recipient = message.recipient
        if sender not in interlocutors and sender != user:
            unread_number = Message.objects.filter(sender=sender, recipient=recipient, check_read_it=False).count()
            last_messages[message] = unread_number
            interlocutors.append(sender)
        if recipient not in interlocutors and recipient != user:
            last_messages[message] = 0
            interlocutors.append(recipient)
    dialogs = {}
    for human in interlocutors:
        messages_single_dialog = Message.objects.filter(sender=human, recipient=user) | Message.objects.filter(
            sender=user, recipient=human)
        dialogs[human] = messages_single_dialog.order_by('sending_time')
    return last_messages, dialogs


def send_message(sender, recipient, text, text_for_sender='', sending_time=datetime.now()):
    message = Message(sender=sender, recipient=recipient, text=text, text_for_sender=text_for_sender,
                      sending_time=sending_time)
    message.save()


def request_permission_tree(tree, requester):
    sending_time = datetime.now()
    text = mes_permission.format(
        tree.get_absolute_url(),
        tree.__str__(),
        reverse('permission_user_request', kwargs={'tree': tree.slug, 'username': requester, 'time': sending_time}),
        reverse('deviation_user_request', kwargs={'tree': tree.slug, 'username': requester, 'time': sending_time})
    )
    text_for_sender = mes_permission_for_sender.format(
        tree.get_absolute_url(),
        tree.__str__())
    tree.potential_user.add(requester)
    send_message(requester, tree.creator, text, text_for_sender, sending_time)


def get_gender(first_name):
    return MorphAnalyzer().parse(first_name)[0].tag.gender


def get_relationships(who, for_whom, tree):
    gender = get_gender(who.first_name)
    if who == for_whom:
        return who_i[gender]
    if who in for_whom.parents.all() or for_whom in who.parents.all():
        return immediate_family_dictionary[gender][who in for_whom.parents.all()]
    tree_humans = tree.humans.all()
    first_human, second_human = who, for_whom
    first_human_list, second_human_list = [who], [for_whom]
    while first_human not in second_human_list and second_human not in first_human_list:
        fhp = (first_human.parents.all() & tree_humans).first()
        shp = (second_human.parents.all() & tree_humans).first()
        if fhp:
            first_human = fhp
            if first_human_list[-1] != first_human:
                first_human_list.append(first_human)
        if shp:
            second_human = shp
            if second_human_list[-1] != second_human:
                second_human_list.append(second_human)
    if first_human in second_human_list:
        kinship_range = second_human_list.index(first_human)
        kinship_range2 = first_human_list.index(first_human)
        generational_difference = kinship_range - kinship_range2
        if len(first_human_list) == 1:
            kinship_range = 0
    else:
        kinship_range = first_human_list.index(second_human)
        kinship_range2 = second_human_list.index(second_human)
        generational_difference = kinship_range2 - kinship_range
        if len(second_human_list) == 1:
            kinship_range = 0
    if abs(generational_difference) > 1:
        kinship_range += 1
    quantity_pra = 0
    if abs(generational_difference) > 2:
        quantity_pra = abs(generational_difference) - 2
        generational_difference = 2 if generational_difference > 2 else -2
    return ''.join([
        f'{kinship_range_dictionary[kinship_range] + gender_end[gender] + " " if kinship_range > 1 else ""}',
        f'{quantity_pra * "пра" if quantity_pra else ""}',
        f'{generational_difference_dictionary[gender][generational_difference]}'
    ]).capitalize()


def validate_username(request):
    username = request.GET.get('username', None)
    response = {
        'is_taken': User.objects.filter(username__iexact=username).exists()
    }
    return JsonResponse(response)


def update_tree(user, trees, count=1):
    for tree in trees:
        people = tree.user.exclude(pk=user.pk)
        for human in people:
            number = NumberChanges.objects.filter(user=human, tree=tree).first()
            if number:
                number.number += count
                number.save()
            else:
                NumberChanges(user=human, tree=tree, number=count).save()


def get_sunburstJSON(child, trees, user, range=0):
    parents = child.parents.all()
    color = gender_color[get_gender(child.first_name)]
    if parents.count() != 0:
        return {
            'name': child.__str__(),
            'who': get_relationships(child, user, (trees.filter(humans=child) & trees.filter(humans=user)).first()),
            'children': [
                get_sunburstJSON(parent, trees, user, range + 1) for parent in parents
            ],
            'normal': {'fill': color}
        }
    else:
        return {
            'name': child.__str__(),
            'who': get_relationships(child, user, (trees.filter(humans=child) & trees.filter(humans=user)).first()),
            'normal': {'fill': color}
        }


def get_child_and_etc(human, people=Human.objects.all(), CAE=None):
    if CAE is None:
        CAE = []
    children = people.filter(parents=human)
    if children.exists():
        CAE.append(human)
        for child in children:
            CAE += get_child_and_etc(child, people)
        return CAE
    else:
        CAE.append(human)
        return CAE
