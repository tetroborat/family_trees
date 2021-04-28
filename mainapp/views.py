import operator

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.contrib import messages
from pymorphy2 import MorphAnalyzer
from django.views import generic
from fuzzywuzzy import process
from .constans import *
from .mixins import *


def get_tree(parent):
    def get_str(p):
        if p.image:
            str_tree = li_tree_with_image.format(p.image.url, p.get_absolute_url('human_detail'), p)
        else:
            str_tree = li_tree.format(p.get_absolute_url('human_detail'), p)
        children = Human.objects.filter(parent=p)
        if children:
            str_tree += '<ul>'
            for child in children:
                str_tree += get_str(child)
            str_tree += '</ul>'
        return str_tree

    return '<ul>' + get_str(parent) + '</ul>'


def get_breadcrumb(human):
    def get_li(h):
        if h.parent:
            return get_li(h.parent) + li_breadcrumb.format(h.get_absolute_url(), h.__str__())
        else:
            return li_breadcrumb.format(h.get_absolute_url(), h.__str__())

    if human.parent:
        return get_li(human.parent) + li_breadcrumb_without_href.format(human.__str__())
    else:
        return li_breadcrumb_without_href.format('Происхождение человека не известно')


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


def get_queryset(request, trees, query, accuracy=60, with_one_username=True):
    people = Human.objects.filter(tree__in=trees)
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
        Tree.objects.all(),
        f'{request.user.first_name} {request.user.last_name}',
        accuracy=90,
        with_one_username=False
    )
    for human in queryset:
        if human.tree not in possible_trees:
            possible_trees.append(human.tree)
    return possible_trees


class BaseTreeView(AuthenticatedMixin, VerificationAccessTreeMixin):

    def get(self, request, **kwargs):
        tree = self.context['auth_user_all_trees'].get(slug=kwargs['tree'])
        unread_number = NumberChanges.objects.filter(user=request.user, tree=tree).first()
        if unread_number:
            unread_number.number = 0
            unread_number.save()
            if tree.creator == request.user:
                self.context['auth_user_trees'][tree] = 0
            else:
                self.context['auth_user_change_trees'][tree] = 0
        self.context.update({
            'tree': tree,
            'title': 'Дерево | {} | Родословная'.format(tree.name.__str__()),
            'delete_tree': tree.get_absolute_url('delete_tree'),
            'journal_tree': tree.get_absolute_url('journal_tree'),
            'people': Human.objects.filter(tree=tree)
        })

        for human in Human.objects.filter(tree=tree):
            if not human.parent:
                get_tree(human)
                self.context.update({
                    'tree_root': human,
                    'human_tree': mark_safe(get_tree(human)),
                })
        return render(request, 'base_tree_view_page.html', self.context)


class HumanDetailView(AuthenticatedMixin, VerificationAccessTreeMixin):
    template_name = 'human_detail_page.html'

    def get_context_data(self, request, **kwargs):
        people = Human.objects.filter(tree=Tree.objects.get(slug=kwargs['tree'], user=request.user))
        human = people.get(slug=kwargs['slug'])
        context = {
            'human': human,
            'user': human.tree.creator,
            'change_info_human': human.get_absolute_url('change_info_human'),
            'delete_human': human.get_absolute_url('delete_human'),
            'delete_photo_human': human.get_absolute_url('delete_photo_human'),
            'title': 'Ближайшие родственики | {} |  Родословная'.format(human.__str__()),
            'children': people.filter(parent=human),
            'human_tree': mark_safe(get_tree(human)),
            'breadcrumb': mark_safe(get_breadcrumb(human))
        }
        for child in context['children']:
            try:
                context['grandsons'] = context['grandsons'] | people.filter(parent=child)
            except KeyError:
                context['grandsons'] = people.filter(parent=child)
        self.context.update(context)
        return self.context

    def get(self, request, **kwargs):
        return render(request, self.template_name, self.get_context_data(request, **kwargs))


class SearchResultView(AuthenticatedMixin):

    def get(self, request):
        query = self.request.GET.get('search_form', )
        self.context.update({
            'object_list': get_queryset(request, Tree.objects.filter(user=request.user), query),
            'users_list': get_users(query),
            'title': f'Поиск | "{query}" | Родословная'
        })
        return render(request, 'search_result_page.html', self.context)


class ChangeHumanDetailView(HumanDetailView, AuthenticatedMixin, VerificationAccessTreeMixin):
    template_name = 'change_human_info_page.html'

    def get_context_data(self, request, **kwargs):
        people = Human.objects.filter(tree=Tree.objects.get(slug=kwargs['tree'], user=request.user))
        context = super().get_context_data(request, **kwargs)
        human = people.get(slug=kwargs['slug'])
        context['title'] = 'Изменение данных | {} | {} | Родословная'.format(human.__str__(), human.tree.name.__str__())
        context['save_human'] = human.get_absolute_url('save_human')
        self.context.update(context)
        return self.context


class SaveHuman(AuthenticatedMixin, VerificationAccessTreeMixin):

    @staticmethod
    def post(request, **kwargs):
        update_human = Human.objects.get(slug=request.path.split('/')[-2],
                                         tree=Tree.objects.get(user=request.user, slug=kwargs['tree']))
        update_human.first_name = request.POST.get('first_name')
        update_human.last_name = request.POST.get('last_name')
        if request.FILES.get('image_human'):
            update_human.image = request.FILES.get('image_human')
        f_p = request.POST.get('first_name_parent')
        l_p = request.POST.get('last_name_parent')
        if f_p or l_p:
            if update_human.parent:
                update_human.parent.first_name = f_p
                update_human.parent.last_name = l_p
                if request.FILES.get('image_parent'):
                    update_human.image = request.FILES.get('image_parent')
                update_human.parent.save()
                messages.info(request, str_human_update.format(update_human.parent.__str__()))
            else:
                new_parent = Human(first_name=f_p,
                                   last_name=l_p,
                                   tree=update_human.tree)
                update_tree(request.user, update_human.tree)
                if request.FILES.get('image_parent'):
                    new_parent.image = request.FILES.get('image_parent')
                new_parent.save()
                messages.success(request, str_human_input_tree.format(new_parent.__str__(), new_parent.tree.__str__()))
                update_human.parent = new_parent
        update_human.save()
        i = 0
        while request.POST.get('first_name_child' + str(i), ):
            f_c, l_c = request.POST.get('first_name_child' + str(i), ), request.POST.get('last_name_child' + str(i), )
            human_search = Human.objects.filter(first_name=f_c,
                                                last_name=l_c,
                                                parent=update_human,
                                                tree=update_human.tree)
            if human_search.exists():
                if request.FILES.get('image_child' + str(i)):
                    human_search[0].image = request.FILES.get('image_child' + str(i))
                    human_search[0].save()
            else:
                child = Human(first_name=f_c,
                              last_name=l_c,
                              parent=update_human,
                              tree=update_human.tree)
                update_tree(request.user, update_human.tree)
                if request.FILES.get('image_child' + str(i)):
                    child.image = request.FILES.get('image_child' + str(i))
                child.save()
                messages.success(request, str_human_input_tree.format(child.__str__(), child.tree.__str__()))
            i += 1
        messages.info(request, str_human_update.format(update_human.__str__()))
        return HttpResponseRedirect(update_human.tree.get_absolute_url())


class DeleteHuman(AuthenticatedMixin, VerificationAccessTreeMixin):

    @staticmethod
    def get(request, **kwargs):
        tree = Tree.objects.get(user=request.user, slug=kwargs['tree'])
        human = Human.objects.get(slug=kwargs['slug'], tree=tree)
        name_human = human.__str__()
        name_tree = human.tree.__str__()
        human.delete()
        messages.error(request, str_human_delete_tree.format(name_human, name_tree))
        if not Human.objects.filter(tree=tree).exists():
            Human(first_name=request.user.first_name,
                  last_name=request.user.last_name,
                  tree=tree).save()
            update_tree(request.user, tree)
        return HttpResponseRedirect(tree.get_absolute_url())


class SignUpView(generic.CreateView):
    form_class = UserCreationForm
    template_name = 'account/signup.html'

    def post(self, request, *args, **kwargs):
        if request.POST.get('password') == request.POST.get('password2'):
            user = User.objects.create_user(username=request.POST.get('username'),
                                            password=request.POST.get('password'))
            messages.success(request, 'Пользователь @{} успешно создан!'.format(user))
        else:
            messages.error(request, 'Пароли не совпадают')
            return HttpResponseRedirect('/signup/')
        user.save()
        return authenticate_user(request)


class UserInfoView(AuthenticatedMixin, VerificationAccessTreeMixin):

    def get(self, request, **kwargs):
        if not (request.user.first_name and Tree.objects.filter(creator=request.user).exists()):
            context = {
                'user': request.user
            }
            if not request.user.first_name:
                return render(request, 'account/welcome_page.html', context)
            return HttpResponseRedirect('/possible_trees/')
        else:
            user = User.objects.get(username=kwargs['username'])
            user_trees = get_dict_tree_and_unread_number(request.user, Tree.objects.filter(creator=user))
            change_user_trees = Tree.objects.filter(user=user)
            list_change_user_trees = []
            for tree in change_user_trees:
                if tree.creator != user:
                    list_change_user_trees.append(tree)
            list_change_user_trees = get_dict_tree_and_unread_number(request.user, list_change_user_trees)
            self.context.update({
                'alien_user': user,
                'title': f'@{user} | Родословная',
                'change_info_user': get_absolute_url_user(user, 'change_info_user'),
                'delete_user_info': get_absolute_url_user(user, 'delete_user'),
                'alien_user_trees': user_trees,
                'alien_user_change_trees': list_change_user_trees if len(list_change_user_trees) > 0 else None
            })
            return render(request, 'user_info_page.html', self.context)

    @staticmethod
    def post(request, **kwargs):
        user = request.user
        checker = True if user.first_name else False
        if request.POST.get('login'):
            user.username = request.POST.get('login')
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        i = 0
        all_known_trees = Tree.objects.filter(creator=request.user)
        for known_tree in all_known_trees:
            tree_name = request.POST.get('line_name' + str(i))
            if tree_name != known_tree.name:
                known_tree.name = tree_name
                known_tree.save()
                for human in Human.objects.filter(tree=known_tree):
                    human.save()
            i += 1
        while request.POST.get('line_name' + str(i)):
            tree_name = request.POST.get('line_name' + str(i))
            tree = Tree(name=tree_name,
                        creator=user)
            tree.save()
            Human(first_name=user.first_name,
                  last_name=user.last_name,
                  tree=tree).save()
            update_tree(request.user, tree)
            i += 1
        user.save()
        if checker:
            messages.success(request, str_user_update.format(user.username))
        return HttpResponseRedirect(get_absolute_url_user(user))


class ChangeUserInfoView(AuthenticatedMixin, VerificationAccessTreeMixin):

    def get(self, request, **kwargs):
        self.context.update({'title': 'Изменение данных | @{} | Родословная'.format(request.user)})
        return render(request, 'change_user_info_page.html', self.context)


class DeleteUser(AuthenticatedMixin, VerificationAccessTreeMixin):

    @staticmethod
    def get(request, **kwargs):
        username = request.user.username
        request.user.delete()
        messages.error(request, str_user_delete.format(username))
        return HttpResponseRedirect('/login/')


class RedirectionBase(AuthenticatedMixin):

    @staticmethod
    def get(request):
        return HttpResponseRedirect(get_absolute_url_user(request.user))


class DeleteTree(AuthenticatedMixin, VerificationAccessTreeMixin):

    @staticmethod
    def get(request, **kwargs):
        tree = Tree.objects.get(user=request.user, slug=kwargs['tree'])
        tree.delete()
        messages.error(request, str_tree_delete.format(tree.name))
        return HttpResponseRedirect(get_absolute_url_user(request.user))


class LoginUser(View):

    @staticmethod
    def get(request):
        if request.user.is_active:
            return HttpResponseRedirect(reverse('user_info', kwargs={'username': request.user.username}))
        return render(request, 'account/login.html')

    @staticmethod
    def post(request):
        return authenticate_user(request)


class LogoutUser(View):

    @staticmethod
    def get(request):
        logout(request)
        return HttpResponseRedirect('/login/')


class JournalTreeView(AuthenticatedMixin, VerificationAccessTreeMixin):

    def get(self, request, *args, **kwargs):
        search_tree = Tree.objects.get(slug=kwargs['tree'])
        users = search_tree.user.all()
        users_tree_list = []
        all_users_list = []
        all_users = User.objects.all()
        for user in users:
            if user != search_tree.creator:
                users_tree_list.append(user)
        for user in all_users:
            if user not in users_tree_list and user != search_tree.creator:
                all_users_list.append(user)
        self.context.update({
            'all_users': all_users_list,
            'title': 'Допущенные к дереву "{}" | Родословная'.format(search_tree),
            'users_tree': users_tree_list,
            'tree': search_tree,
            'permission_user': search_tree.get_absolute_url('permission_user')
        })
        return render(request, 'journal_tree_page.html', self.context)


class PermissionUser(AuthenticatedMixin, VerificationAccessTreeMixin):

    @staticmethod
    def post(request, **kwargs):
        tree = Tree.objects.get(slug=kwargs['tree'])
        user = User.objects.get(username=request.POST.get('login').split(' ')[0])
        tree.user.add(user)
        messages.success(request, str_user_accept_tree.format(user, tree))
        return HttpResponseRedirect(tree.get_absolute_url('journal_tree'))

    @staticmethod
    def get(request, **kwargs):
        tree = Tree.objects.get(slug=kwargs['tree'])
        user = User.objects.get(username=kwargs['username'])
        tree.user.add(user)
        messages.success(request, str_user_accept_tree.format(user, tree))
        message = Message.objects.get(sending_time=kwargs['time'], recipient=request.user)
        message.check_read_it = True
        message.text = mark_safe(mes_permission_success.format(tree.get_absolute_url(), tree.name))
        message.text_for_sender = mark_safe(
            mes_permission_for_sender_success.format(tree.get_absolute_url(), tree.name))
        message.save()
        return HttpResponseRedirect(tree.get_absolute_url('journal_tree'))


class DeviationUser(AuthenticatedMixin, VerificationAccessTreeMixin):

    @staticmethod
    def get(request, **kwargs):
        tree = Tree.objects.get(slug=kwargs['tree'])
        message = Message.objects.get(sending_time=kwargs['time'], recipient=request.user)
        message.text = mark_safe(mes_permission_deviation.format(tree.get_absolute_url(), tree.name))
        message.check_read_it = True
        message.text_for_sender = mark_safe(
            mes_permission_for_sender_deviation.format(tree.get_absolute_url(), tree.name))
        message.save()
        return HttpResponseRedirect('/messages/')


class TerminationAccess(AuthenticatedMixin, VerificationAccessTreeMixin):

    @staticmethod
    def get(request, **kwargs):
        tree = Tree.objects.get(slug=kwargs['tree'])
        user = User.objects.get(username=kwargs['username'])
        tree.user.remove(user)
        messages.error(request, str_user_dontaccept_tree.format(user, tree))
        return HttpResponseRedirect(tree.get_absolute_url('journal_tree'))


class DeletePhotoHuman(AuthenticatedMixin, VerificationAccessTreeMixin):

    @staticmethod
    def get(request, **kwargs):
        human = Human.objects.get(tree=Tree.objects.get(user=request.user, slug=kwargs['tree']), slug=kwargs['slug'])
        human.image = None
        human.save()
        messages.error(request, 'Фото человека {} удалено из дерева "{}"'.format(human, human.tree))
        return HttpResponseRedirect(human.get_absolute_url())


class PossibleTreesView(AuthenticatedMixin):

    @staticmethod
    def get(request, **kwargs):
        context = {
            'possible_trees': get_possible_trees(request),
            'user_name': f'{request.user.first_name} {request.user.last_name}'
        }
        return render(request, 'possible_trees_page.html', context)

    @staticmethod
    def post(request, **kwargs):
        user = request.user
        possible_trees = get_possible_trees(request)
        for tree in possible_trees:
            request_permission_tree(tree, user)
        i = 0
        while request.POST.get('line_name' + str(i)):
            tree_name = request.POST.get('line_name' + str(i))
            tree = Tree(name=tree_name,
                        creator=user)
            tree.save()
            Human(first_name=user.first_name,
                  last_name=user.last_name,
                  tree=tree).save()
            update_tree(request.user, tree)
            i += 1
        user.save()
        return HttpResponseRedirect(get_absolute_url_user(user))


class MessagesView(AuthenticatedMixin):

    def get(self, request, **kwargs):
        last_messages, dialogs = get_last_messages_and_dialogs(request.user)
        self.context.update({
            'title': 'Запросы | Родословная',
            'last_messages': last_messages,
            'dialogs': dialogs
        })
        return render(request, 'messages_page.html', self.context)


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
    text = mark_safe(mes_permission.format(
        tree.get_absolute_url(),
        tree.name,
        reverse('permission_user_request', kwargs={'tree': tree.slug, 'username': requester, 'time': sending_time}),
        reverse('deviation_user_request', kwargs={'tree': tree.slug, 'username': requester, 'time': sending_time})
    ))
    text_for_sender = mark_safe(mes_permission_for_sender.format(
        tree.get_absolute_url(),
        tree.name))
    send_message(requester, tree.creator, text, text_for_sender, sending_time)


class SendAccessRequestTree(AuthenticatedMixin):
    @staticmethod
    def get(request, **kwargs):
        request_permission_tree(Tree.objects.get(slug=kwargs['tree']), request.user)
        return HttpResponseRedirect('/messages/')


def related_relationships(request, tree):
    first_name_str = request.GET.get('first_human', None).split()
    second_name_str = request.GET.get('second_human', None).split()
    tree = Tree.objects.get(slug=tree)
    if len(first_name_str) > 0:
        try:
            first_human = Human.objects.filter(tree=tree, first_name=first_name_str[0],
                                               last_name=first_name_str[1]).first()
        except IndexError:
            first_human = Human.objects.filter(tree=tree, first_name=first_name_str[0]).first()
    else:
        first_human = None
    if len(second_name_str) > 0:
        try:
            second_human = Human.objects.filter(tree=tree, first_name=second_name_str[0],
                                                last_name=second_name_str[1]).first()
        except IndexError:
            second_human = Human.objects.filter(tree=tree, first_name=second_name_str[0]).first()
    else:
        second_human = None
    response = {
        'first_human': True if first_human is not None else False,
        'second_human': True if second_human is not None else False
    }
    if response['first_human'] and response['second_human']:
        response.update({
            'who_is_who': get_relationships(first_human, second_human)
        })
    return JsonResponse(response)


def get_relationships(who, for_whom):
    gender = MorphAnalyzer().parse(who.first_name)[0].tag.gender
    if who == for_whom:
        return who_i[gender]
    first_human, second_human = who, for_whom
    first_human_list, second_human_list = [who], [for_whom]
    while first_human not in second_human_list and second_human not in first_human_list:
        if first_human.parent is not None:
            first_human = first_human.parent
        if second_human.parent is not None:
            second_human = second_human.parent
        if first_human_list[-1] != first_human:
            first_human_list.append(first_human)
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
        f'{immediate_family_dictionary[gender][generational_difference] if kinship_range < 3 and kinship_range2 < 3 else generational_difference_dictionary[gender][generational_difference]}'
    ]).capitalize()


def validate_username(request):
    username = request.GET.get('username', None)
    response = {
        'is_taken': User.objects.filter(username__iexact=username).exists()
    }
    return JsonResponse(response)


def update_tree(user, tree):
    people = tree.user.exclude(pk=user.pk)
    for human in people:
        number = NumberChanges.objects.filter(user=human, tree=tree).first()
        if number:
            number.number += 1
            number.save()
        else:
            NumberChanges(user=human, tree=tree, number=1).save()
