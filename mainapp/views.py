
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.db.models import Count
from django.views import generic
from .mixins import *
import json

from mainapp.help_function import *


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
            'title': 'Дерево | {} | Родословная'.format(tree.__str__()),
            'delete_tree': tree.get_absolute_url('delete_tree'),
            'journal_tree': tree.get_absolute_url('journal_tree'),
            'tree_root': tree.oldest_human,
            'human_tree': mark_safe(get_tree(tree.oldest_human, tree.humans.all()))
        })
        return render(request, 'base_tree_view_page.html', self.context)


class HumanDetailView(AuthenticatedMixin):
    template_name = 'human_detail_page.html'

    def get_context_data(self, request, **kwargs):
        people = Human.objects.all()
        human = people.get(slug=kwargs['slug'])
        context = {
            'human': human,
            'change_info_human': human.get_absolute_url('change_info_human'),
            'delete_human': human.get_absolute_url('delete_human'),
            'delete_photo_human': human.get_absolute_url('delete_photo_human'),
            'title': 'Ближайшие родственики | {} |  Родословная'.format(human.__str__()),
            'children': people.filter(parents=human).order_by('date_of_birth'),
            'human_tree': mark_safe(get_tree(human, people))
        }
        for child in context['children']:
            try:
                context['grandsons'] = context['grandsons'] | people.filter(parents=child)
            except KeyError:
                context['grandsons'] = people.filter(parents=child)
        if 'grandsons' in context.keys() :
            context['grandsons'] = context['grandsons'].order_by('date_of_birth')
        self.context.update(context)
        return self.context

    def get(self, request, **kwargs):
        return render(request, self.template_name, self.get_context_data(request, **kwargs))


class SearchResultView(AuthenticatedMixin):

    def get(self, request):
        query = self.request.GET.get('search_form', )
        self.context.update({
            'object_list': get_queryset(request, query),
            'users_list': get_users(query),
            'title': f'Поиск | "{query}" | Родословная'
        })
        return render(request, 'search_result_page.html', self.context)


class ChangeHumanDetailView(HumanDetailView, AuthenticatedMixin):
    template_name = 'change_human_info_page.html'

    def get_context_data(self, request, **kwargs):
        context = super().get_context_data(request, **kwargs)
        human = Human.objects.get(slug=kwargs['slug'])
        context['title'] = f'Изменение данных | {human.__str__()} | Родословная'
        context['save_human'] = human.get_absolute_url('save_human')
        self.context.update(context)
        return self.context


class SaveHuman(AuthenticatedMixin):

    @staticmethod
    def post(request, **kwargs):
        potential_people = {}
        humans = Human.objects.all()
        trees = Tree.objects.all()
        updating_human = humans.get(slug=kwargs['slug'])
        updating_human.first_name = request.POST.get('first_name')
        updating_human.last_name = request.POST.get('last_name')
        if request.POST.get('date_of_birth'):
            updating_human.date_of_birth = request.POST.get('date_of_birth')
        if request.FILES.get('image_human'):
            updating_human.image = request.FILES.get('image_human')
        i = 0
        while request.POST.get('first_name_parent' + str(i), ):
            f_c, l_c = request.POST.get('first_name_parent' + str(i), ), request.POST.get('last_name_parent' + str(i), )
            human_search = updating_human.parents.filter(
                first_name=f_c,
                last_name=l_c
            )
            if human_search.exists():
                parent = human_search[0]
                if request.FILES.get('image_parent' + str(i)):
                    parent.image = request.FILES.get('image_parent' + str(i))
                if request.POST.get('date_of_birth_parent' + str(i)):
                    parent.date_of_birth = request.POST.get('date_of_birth_parent' + str(i))
                parent.save()
            else:
                potential_human = humans.filter(
                    first_name=f_c,
                    last_name=l_c
                )
                if not potential_human.exists():
                    parent = Human(
                        first_name=f_c,
                        last_name=l_c,
                        image=request.FILES.get('image_parent' + str(i)),
                        date_of_birth=request.POST.get('date_of_birth_parent' + str(i)) if request.POST.get('date_of_birth_parent' + str(i)) else None
                    )
                    parent.save()
                    if updating_human.parents.exists():
                        first_parent = updating_human.parents.first()
                        if humans.filter(parents=first_parent).exclude(pk=updating_human.pk).exists():
                            children = humans.filter(parents=first_parent)
                            potential_people.update({
                                'potential_parent_for_other': [parent, children, children[0].parents.all().first()]
                            })
                        new_tree = Tree(
                            creator=request.user,
                            oldest_human=parent
                        )
                        new_tree.save()
                        CAE = get_child_and_etc(updating_human)
                        for human in CAE:
                            new_tree.humans.add(human)
                            if human.user:
                                new_tree.user.add(human.user)
                        new_tree.user.add(request.user)
                        new_tree.humans.add(parent)
                        new_tree.save()
                        update_tree(request.user, [new_tree], len(CAE) + 1)
                    else:
                        updating_tree = trees.get(oldest_human=updating_human)
                        updating_tree.oldest_human = parent
                        updating_tree.humans.add(parent)
                        updating_tree.save()
                        update_tree(request.user, trees.filter(humans=updating_human))
                    updating_human.parents.add(parent)
                    if request.FILES.get('image_parent' + str(i)):
                        parent.image = request.FILES.get('image_parent' + str(i))
                    parent.save()
                    messages.success(request, str_human_input_tree.format(parent.__str__()))
                else:
                    potential_people.update({
                        potential_human[0]: 'parent'
                    })
            i += 1
        updating_human.save()
        i = 0
        while request.POST.get('first_name_child' + str(i), ):
            f_c, l_c = request.POST.get('first_name_child' + str(i), ), request.POST.get('last_name_child' + str(i), )
            human_search = humans.filter(
                parents=updating_human,
                first_name=f_c,
                last_name=l_c
            )
            if human_search.exists():
                child = human_search[0]
                if request.FILES.get('image_child' + str(i)):
                    child.image = request.FILES.get('image_child' + str(i))
                if request.POST.get('date_of_birth_child' + str(i)):
                    child.date_of_birth = request.POST.get('date_of_birth_child' + str(i))
                child.save()
            else:
                potential_human = humans.filter(
                    first_name=f_c,
                    last_name=l_c
                )
                if not potential_human.exists():
                    child = Human(
                        first_name=f_c,
                        last_name=l_c,
                        image=request.FILES.get('image_child' + str(i)),
                        date_of_birth=request.POST.get('date_of_birth_child' + str(i)) if request.POST.get('date_of_birth_child' + str(i)) else None
                    )
                    child.save()
                    child.parents.add(updating_human)
                    child.save()

                    for tree in trees.filter(humans=updating_human):
                        tree.humans.add(child)
                    update_tree(request.user, updating_human.trees.all())
                    messages.success(request, str_human_input_tree.format(child.__str__()))
                else:
                    potential_people.update({
                        potential_human[0]: 'child'
                    })
            i += 1
        count_parents_child = humans.annotate(count_parents=Count('parents')).filter(parents=updating_human)
        two_parents_child = count_parents_child.filter(count_parents=2)
        one_parents_child = count_parents_child.filter(count_parents=1)
        if two_parents_child.exists() and one_parents_child.exists():
            potential_people.update({
                'potential_parent_for_other': [two_parents_child.first().parents.exclude(pk=updating_human.pk).first(), one_parents_child, updating_human]
            })
        if len(potential_people) > 0:
            potential_people.update({
                updating_human: 'human'
            })
            return PotentialHumanView.get(request, potential_people=potential_people)
        messages.info(request, str_human_update.format(updating_human.__str__()))
        return HttpResponseRedirect(updating_human.get_absolute_url())


class DeleteHuman(AuthenticatedMixin):

    @staticmethod
    def get(request, **kwargs):
        humans = Human.objects.all()
        human = humans.get(slug=kwargs['slug'])
        if human.user == request.user:
            messages.error(request, 'Нельзя удалить самого себя')
            return HttpResponseRedirect('/')
        children = humans.filter(parents=human)
        trees = Tree.objects.filter(humans=human)
        tree = trees.filter(oldest_human=human)
        if tree.exists():
            tree = tree[0]
            if children.exists():
                if children.count() == 1:
                    if children[0].parents.count() == 1:
                        tree.oldest_human = children[0]
                        tree.save()
                    else:
                        tree.delete()
                else:
                    for child in children:
                        new_tree = Tree(
                            creator=request.user,
                            oldest_human=child
                        )
                        new_tree.save()
                        for user in trees.values('user').filter(humans=child):
                            new_tree.user.add(User.objects.get(id=user['user']))
                        for item_human in get_child_and_etc(child):
                            new_tree.humans.add(item_human)
                        new_tree.save()
            else:
                tree.delete()
        else:
            if children.exists():
                CAE = get_child_and_etc(human)
                for child in children:
                    if child.parents.count() == 1:
                        new_tree = Tree(
                            creator=request.user,
                            oldest_human=child
                        )
                        new_tree.save()
                        for user in trees.filter(humans=child).values('user'):
                            new_tree.user.add(User.objects.get(id=user['user']))
                        for item_human in get_child_and_etc(child):
                            new_tree.humans.add(item_human)
                        new_tree.save()
                for tree in trees:
                    for item_human in CAE:
                        tree.humans.remove(item_human)
        for item_tree in trees:
            item_tree.humans.remove(human)
            item_tree.save()
        name_human = human.__str__()
        human.delete()
        messages.error(request, str_human_delete_tree.format(name_human))
        return HttpResponseRedirect('/')


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


class UserInfoView(AuthenticatedMixin):

    def get(self, request, **kwargs):
        trees = Tree.objects.all()
        if not (trees.filter(user=request.user).exists()):
            context = {
                'user': request.user
            }
            if not request.user.first_name:
                return render(request, 'account/welcome_page.html', context)
            return HttpResponseRedirect('/possible_trees/')
        else:
            user = User.objects.get(username=kwargs['username'])
            user_trees = get_dict_tree_and_unread_number(request.user, trees.filter(creator=user))
            change_user_trees = trees.filter(user=user)
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
        user.save()
        if checker:
            messages.success(request, str_user_update.format(user.username))
        return HttpResponseRedirect(get_absolute_url_user(user))


class ChangeUserInfoView(AuthenticatedMixin):

    def get(self, request, **kwargs):
        self.context.update({'title': 'Изменение данных | @{} | Родословная'.format(request.user)})
        return render(request, 'change_user_info_page.html', self.context)


class DeleteUser(AuthenticatedMixin):

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


class DeleteTree(AuthenticatedMixin):

    @staticmethod
    def get(request, **kwargs):
        trees = Tree.objects.all()
        tree = trees.get(user=request.user, slug=kwargs['tree'])
        messages.error(request, str_tree_delete.format(tree))
        for human in tree.humans.all():
            if trees.filter(humans=human).count() == 1:
                human.delete()
        tree.delete()
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
        for user in users:
            if user != search_tree.creator:
                users_tree_list.append(user)
        all_users_list = User.objects.exclude(pk__in=[item.pk for item in users])
        self.context.update({
            'all_users': all_users_list,
            'title': 'Допущенные к дереву "{}" | Родословная'.format(search_tree),
            'users_tree': users_tree_list,
            'tree': search_tree,
            'permission_user': search_tree.get_absolute_url('permission_user')
        })
        return render(request, 'journal_tree_page.html', self.context)


class PermissionUser(AuthenticatedMixin):

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
        message.text = mark_safe(mes_permission_success.format(tree.get_absolute_url(), tree))
        message.text_for_sender = mark_safe(
            mes_permission_for_sender_success.format(tree.get_absolute_url(), tree))
        message.save()
        tree.potential_user.remove(message.sender)
        tree.save()
        NumberChanges(user=message.sender, tree=tree, number=tree.get_count_human().split()[0]).save()
        return HttpResponseRedirect(tree.get_absolute_url('journal_tree'))


class DeviationUser(AuthenticatedMixin):

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


class TerminationAccess(AuthenticatedMixin):

    @staticmethod
    def get(request, **kwargs):
        tree = Tree.objects.get(slug=kwargs['tree'])
        user = User.objects.get(username=kwargs['username'])
        tree.user.remove(user)
        if user != request.user:
            text_for_sender = f'''Вы запретили пользователю 
            <a href="/user_info/{user.username}/">
            <span class="shadow badge rounded-pill bg-info text-dark">
                {user.first_name} {user.last_name} 
            </span> 
            </a>
            доступ к дереву 
            <a href="{tree.get_absolute_url()}">
            <span class="shadow badge rounded-pill bg-success text-dark">
                {tree}
            </span>
            </a>
            '''
            text = f'''Пользователь 
            <a href="/user_info/{request.user.username}/">
            <span class="shadow badge rounded-pill bg-info text-dark">
                {request.user.first_name} {request.user.last_name} 
            </span></a> 
            запретил Вам доступ к дереву 
            <a href="{tree.get_absolute_url()}">
            <span class="shadow badge rounded-pill bg-success text-dark">
                {tree}
            </span>
            </a>
            '''
            send_message(request.user, user, text, text_for_sender, sending_time=datetime.now())

        messages.error(request, str_user_dontaccept_tree.format(user, tree))
        return HttpResponseRedirect(tree.get_absolute_url('journal_tree'))


class DeletePhotoHuman(AuthenticatedMixin):

    @staticmethod
    def get(request, **kwargs):
        human = Human.objects.get(slug=kwargs['slug'])
        human.image = None
        human.save()
        messages.error(request, 'Фото человека {} удалено'.format(human))
        return HttpResponseRedirect(human.get_absolute_url())


class PossibleTreesView(AuthenticatedMixin):

    @staticmethod
    def get(request, **kwargs):
        possible_trees = get_possible_trees(request) if 'uncheck' not in kwargs.keys() else []
        fn, ln = request.user.first_name, request.user.last_name
        context = {
            'user_name': f'{fn} {ln}',
            'uncheck': False if 'uncheck' not in kwargs.keys() else True
        }
        if len(possible_trees) > 0:
            humans = Human.objects.all()
            user_human = humans.filter(first_name=fn, last_name=ln).first()
            context.update({
                'possible_trees': possible_trees,
                'user_human': user_human,
                'relatives': {
                    'parent': user_human.parents.all(),
                    'children': humans.filter(parents=user_human)
                }
            })
        return render(request, 'possible_trees_page.html', context)

    @staticmethod
    def post(request, **kwargs):
        user = request.user
        check_list = request.POST.getlist('check')
        uncheck_list = request.POST.getlist('uncheck')
        humans = Human.objects.all()
        human_user = humans.filter(user=user)
        human_user = human_user[0] if human_user.exists() else \
            Human(
                first_name=user.first_name,
                last_name=user.last_name,
                user=user
            )
        human_user.save()
        if check_list:
            human_user.delete()
            search_human = humans.get(pk=check_list[0])
            search_human.user = user
            search_human.save()
            for tree in Tree.objects.filter(humans=search_human):
                tree.user.add(user)
                tree.save()
            return HttpResponseRedirect(get_absolute_url_user(user))
        elif uncheck_list:
            return PossibleTreesView.get(request, uncheck=True)
        i = 0
        while request.POST.get('first_name' + str(i)):
            parent = Human(
                first_name=request.POST.get('first_name' + str(i)),
                last_name=request.POST.get('last_name' + str(i))
            )
            parent.save()
            tree = Tree(
                oldest_human=parent,
                creator=user
            )
            tree.save()
            tree.user.add(user)
            tree.humans.add(parent)
            human_user.parents.add(parent)
            tree.humans.add(parent)
            tree.humans.add(human_user)
            tree.save()
            i += 1
        human_user.save()
        return HttpResponseRedirect(get_absolute_url_user(user))


class MessagesView(AuthenticatedMixin):

    def get(self, request, **kwargs):
        last_messages, dialogs = get_last_messages_and_dialogs(request.user)
        self.context.update({
            'title': 'Запросы | Родословная',
            'last_messages': last_messages,
            'dialogs': dialogs,
            'user': request.user
        })
        return render(request, 'messages_page.html', self.context)


class SendAccessRequestTree(AuthenticatedMixin):
    @staticmethod
    def get(request, **kwargs):
        request_permission_tree(Tree.objects.get(slug=kwargs['tree']), request.user)
        return HttpResponseRedirect('/messages/')


class SunburstView(AuthenticatedMixin):

    def get(self, request):
        human_user = Human.objects.get(user=request.user)
        sunburst = json.dumps([
            get_sunburstJSON(
                human_user,
                Tree.objects.filter(humans=human_user),
                human_user
            )
        ])
        self.context.update({
            'sunburstJSON': sunburst,
            'title': 'Прямые прародители | Родословная'
        })
        return render(request, 'sunburst_relatives.html', self.context)


class PotentialHumanView(AuthenticatedMixin):

    @staticmethod
    def get(request, **kwargs):
        potential_people = kwargs['potential_people']
        humans = Human.objects.all()
        potential_people_context = {
            'parent': {},
            'child': {},
        }
        for human, who in potential_people.items():
            if who != 'human' and human != 'potential_parent_for_other':
                potential_people_context[who][human] = {
                    'parent': human.parents.all(),
                    'children': humans.filter(parents=human)
                }
            else:
                updating_human = human
        user = request.user
        trees = Tree.objects.all()
        user_trees = trees.filter(creator=user)
        change_user_trees = trees.filter(user=user)
        dict_change_trees_unread_number = {}
        for tree in change_user_trees:
            number = NumberChanges.objects.filter(tree=tree, user=user).first()
            dict_change_trees_unread_number[tree] = number.number if number else 0
        list_change_user_trees = []
        for tree in change_user_trees:
            if tree.creator != user:
                list_change_user_trees.append(tree)
        context = {
            'title': 'Возможные совпадения | Родословная',
            'potential_people': potential_people_context,
            'check_pot_people': True if len(potential_people_context['parent']) > 0 or len(potential_people_context['child']) > 0 else False,
            'human': updating_human,
            'auth_user': user,
            'user_info': reverse('user_info', kwargs={'username': user.username}),
            'number_unread_messages': Message.get_number_unread_messages(user),
            'auth_user_all_trees': Tree.objects.filter(user=user),
            'auth_user_change_trees': get_dict_tree_and_unread_number(user, list_change_user_trees),
            'auth_user_trees': get_dict_tree_and_unread_number(user, user_trees)
        }
        if 'potential_parent_for_other' in potential_people.keys():
            context.update({
                'parent_for_other': potential_people['potential_parent_for_other'][2],
                'potential_parent_for_other': potential_people['potential_parent_for_other'][0],
                'potential_child_for_potential_parent': {
                    child: {
                        'parent': child.parents.all(),
                        'children': humans.filter(parents=child)
                    }
                    for child in potential_people['potential_parent_for_other'][1].exclude(pk=updating_human.pk)}
            })
        return render(request, 'potential_human_page.html', context)

    @staticmethod
    def post(request):
        humans = Human.objects.all()
        trees = Tree.objects.all()
        users = User.objects.all()
        check_list = request.POST.getlist('check')
        uncheck_list = list(set(request.POST.getlist('uncheck')).difference(set(check_list)))
        if check_list or uncheck_list:
            who = humans.get(pk=uncheck_list[0].split('_')[0]) if len(uncheck_list) > 0 else humans.get(
                pk=check_list[0].split('_')[0])
            CAE_who = get_child_and_etc(who)
            for who_for_whom in check_list:
                who_for_whom = who_for_whom.split('_')
                relation, whom = who_for_whom[1], humans.get(pk=who_for_whom[2])
                if relation == 'parent':
                    who.parents.add(whom)
                    who.save()
                    who_is_oldest_in_trees = trees.filter(oldest_human=who)
                    whom_trees = trees.filter(humans=whom)
                    if who_is_oldest_in_trees.exists():
                        for tree in who_is_oldest_in_trees:
                            tree.delete()
                    for iter_tree in whom_trees:
                        iter_tree.user.add(request.user)
                        for iter_human in CAE_who:
                            iter_tree.humans.add(iter_human)
                        iter_tree.save()
                    update_tree(request.user, whom_trees, len(CAE_who))
                else:
                    whom.parents.add(who)
                    whom.save()
                    whom_is_oldest_in_trees = trees.filter(oldest_human=whom)
                    who_trees = trees.filter(humans=who)
                    CAE_whom = get_child_and_etc(whom)
                    if whom_is_oldest_in_trees.exists():
                        whom_is_oldest_in_trees[0].delete()
                    for iter_tree in who_trees:
                        for iter_human in CAE_whom:
                            iter_tree.humans.add(iter_human)
                            if iter_human.user:
                                iter_tree.user.add(iter_human.user)
                        iter_tree.save()
                    update_tree(request.user, who_trees, len(CAE_whom))
            for who_for_whom in uncheck_list:
                who_for_whom = who_for_whom.split('_')
                relation, whom = who_for_whom[1], humans.get(pk=who_for_whom[2])
                if relation == 'parent':
                    parent = Human(
                        first_name=whom.first_name,
                        last_name=whom.last_name
                    )
                    parent.save()
                    if who.parents.exists():
                        new_tree = Tree(
                            creator=request.user,
                            oldest_human=parent
                        )
                        new_tree.save()
                        for user in trees.values('user').filter(humans=who):
                            new_tree.user.add(users.get(id=user['user']))
                        for human in CAE_who:
                            new_tree.humans.add(human)
                        new_tree.humans.add(parent)
                        new_tree.save()
                        update_tree(request.user, [new_tree], len(CAE_who))
                    else:
                        updating_tree = trees.get(oldest_human=who)
                        updating_tree.oldest_human = parent
                        updating_tree.humans.add(parent)
                        updating_tree.save()
                        update_tree(request.user, [updating_tree])
                    who.parents.add(parent)
                    parent.save()
                    messages.success(request, str_human_input_tree.format(parent.__str__()))
                else:
                    child = Human(
                        first_name=whom.first_name,
                        last_name=whom.last_name
                    )
                    child.save()
                    child.parents.add(who)
                    for tree in trees.filter(humans=who):
                        tree.humans.add(child)
                    update_tree(request.user, who.trees.all())
                    child.save()
                    messages.success(request, str_human_input_tree.format(child.__str__()))
        par_check_list = request.POST.getlist('par_check')
        if par_check_list:
            who = humans.get(pk=par_check_list[0].split('_')[0])
            for who_for_whom in par_check_list:
                who_for_whom = who_for_whom.split('_')
                whom = humans.get(pk=who_for_whom[2])
                whom.parents.add(who)
                whom.save()
            tree = trees.get(oldest_human=who)
            CAE = get_child_and_etc(who)
            for human in CAE:
                tree.humans.add(human)
            tree.save()
            update_tree(request.user, trees.filter(humans=who), len(par_check_list))
        return HttpResponseRedirect('/')


def related_relationships(request, tree):
    first_name_str = request.GET.get('first_human', None).split()
    second_name_str = request.GET.get('second_human', None).split()
    tree = Tree.objects.get(slug=tree)
    humans = tree.humans.all()
    if len(first_name_str) > 0:
        try:
            first_human = humans.filter(first_name=first_name_str[0],
                                        last_name=first_name_str[1]).first()
        except IndexError:
            first_human = humans.filter(first_name=first_name_str[0]).first()
    else:
        first_human = None
    if len(second_name_str) > 0:
        try:
            second_human = humans.filter(first_name=second_name_str[0],
                                         last_name=second_name_str[1]).first()
        except IndexError:
            second_human = humans.filter(first_name=second_name_str[0]).first()
    else:
        second_human = None
    response = {
        'first_human': True if first_human is not None else False,
        'second_human': True if second_human is not None else False
    }
    if response['first_human'] and response['second_human']:
        response.update({
            'who_is_who': get_relationships(first_human, second_human, tree)
        })
    return JsonResponse(response)


def read_messages_for_id(request):
    user_id = request.GET.get('user_id', None)
    for message in Message.objects.filter(check_read_it=False, sender=User.objects.get(pk=user_id)):
        message.check_read_it = True
        message.save()
    return JsonResponse({})
