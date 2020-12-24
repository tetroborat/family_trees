from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from django.contrib import messages
from django.views import generic
from fuzzywuzzy import process
from .constans import *
from .models import *
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
            return li_breadcrumb.format(h.tree.get_absolute_url(), h.tree.__str__()) + \
                   li_breadcrumb.format(h.get_absolute_url(), h.__str__())

    if human.parent:
        return get_li(human.parent) + '<lii class="breadcrumb-item active" aria-current="page">{}</lii>'.format(
            human.__str__())
    else:
        return li_breadcrumb.format(human.tree.get_absolute_url(), human.tree.__str__()) + \
               '<lii class="breadcrumb-item active" aria-current="page">{}</lii>'.format(human.__str__())


def get_absolute_url_user(user, name_path='user_info'):
    return reverse(name_path, kwargs={'username': user.username})


def authenticate_user(request):
    if User.objects.filter(username=request.POST.get('username')).count() == 0:
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


class BaseTreeView(AuthenticatedMixin):

    def get(self, request, **kwargs):
        for human in Human.objects.filter(tree=self.context['auth_user_all_trees'].get(slug=kwargs['tree'])):
            if not human.parent:
                get_tree(human)
                self.context.update({
                    'tree': human.tree,
                    'user': human.tree.creator,
                    'title': 'Дерево | {} | Родословная'.format(human.tree.__str__()),
                    'human_tree': mark_safe(get_tree(human)),
                    'delete_tree': human.tree.get_absolute_url('delete_tree'),
                    'journal_tree': human.tree.get_absolute_url('journal_tree')
                })
        return render(request, 'base_tree_view_page.html', self.context)


class HumanDetailView(AuthenticatedMixin):
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
        self.context.update({
            'object_list': self.get_queryset(request),
            'title': 'Поиск | "{}" | Родословная'.format(self.query)})
        return render(request, 'search_result_page.html', self.context)

    def get_queryset(self, request):
        self.query = self.request.GET.get('search_form', )
        name_all_people = []
        for tree in self.context['auth_user_trees']:
            try:
                people = people | Human.objects.filter(tree=tree)
            except UnboundLocalError:
                people = Human.objects.filter(tree=tree)
        object_list = []
        username_human = '{} {}'.format(request.user.first_name, request.user.last_name)
        for human in people:
            if human.__str__() != username_human:
                name_all_people.append(human.__str__())
        name_all_people.append(username_human)
        search_human = process.extract(self.query, name_all_people, limit=20)
        for human in search_human:
            if human[1] > 60:
                if len(human[0].split(' ')) > 1:
                    f, l = human[0].split(' ')[0], human[0].split(' ')[1]
                else:
                    f, l = human[0].split(' ')[0], None
                object_list.append(people.get(first_name=f, last_name=l))
        try:
            return object_list
        except UnboundLocalError:
            pass


class ChangeHumanDetailView(HumanDetailView, AuthenticatedMixin):
    template_name = 'change_human_info_page.html'

    def get_context_data(self, request, **kwargs):
        people = Human.objects.filter(tree=Tree.objects.get(slug=kwargs['tree'], user=request.user))
        context = super().get_context_data(request, **kwargs)
        human = people.get(slug=kwargs['slug'])
        context['title'] = 'Изменение данных | {} | {} | Родословная'.format(human.__str__(), human.tree.__str__())
        context['save_human'] = human.get_absolute_url('save_human')
        self.context.update(context)
        return self.context


class SaveHuman(AuthenticatedMixin):

    @staticmethod
    def post(request, **kwargs):
        update_human = Human.objects.get(slug=request.path.split('/')[-2], tree=Tree.objects.get(user=request.user, slug=kwargs['tree']))
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
            if human_search.count() == 0:
                child = Human(first_name=f_c,
                              last_name=l_c,
                              parent=update_human,
                              tree=update_human.tree)
                if request.FILES.get('image_child' + str(i)):
                    child.image = request.FILES.get('image_child' + str(i))
                child.save()
                messages.success(request, str_human_input_tree.format(child.__str__(), child.tree.__str__()))
            else:
                if request.FILES.get('image_child' + str(i)):
                    human_search[0].image = request.FILES.get('image_child' + str(i))
                    human_search[0].save()
            i += 1
        messages.info(request, str_human_update.format(update_human.__str__()))
        return HttpResponseRedirect(update_human.tree.get_absolute_url())


class DeleteHuman(AuthenticatedMixin):

    @staticmethod
    def get(request, **kwargs):
        tree = Tree.objects.get(user=request.user, slug=kwargs['tree'])
        human = Human.objects.get(slug=kwargs['slug'], tree=tree)
        name_human = human.__str__()
        name_tree = human.tree.__str__()
        human.delete()
        messages.error(request, str_human_delete_tree.format(name_human, name_tree))
        if not Human.objects.filter(tree=tree):
            Human(first_name=request.user.first_name,
                  last_name=request.user.last_name,
                  tree=tree).save()
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


class UserInfoView(AuthenticatedMixin):

    def get(self, request, **kwargs):
        if not request.user.first_name:
            return render(request, 'account/welcome_page.html', {})
        else:
            user = User.objects.get(username=kwargs['username'])
            user_trees = Tree.objects.filter(creator=user)
            change_user_trees = Tree.objects.filter(user=user)
            list_change_user_trees = []
            for tree in change_user_trees:
                if tree.creator != user:
                    list_change_user_trees.append(tree)
            self.context.update({
                'trees_info': Tree.objects.filter(user=user),
                'alien_user': user,
                'title': '@{} | Родословная'.format(user),
                'change_info_user': get_absolute_url_user(user, 'change_info_user'),
                'delete_user_info': get_absolute_url_user(user, 'delete_user'),
                'alien_user_trees': user_trees,
                'alien_user_change_trees': list_change_user_trees
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
        all_known_trees = Tree.objects.filter(user=request.user)
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
            i += 1
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
        tree = Tree.objects.get(user=request.user, slug=kwargs['tree'])
        name_tree = tree.__str__()
        tree.delete()
        messages.error(request, str_tree_delete.format(name_tree))
        return HttpResponseRedirect(get_absolute_url_user(request.user))


class LoginUser(View):

    @staticmethod
    def get(request):
        return render(request, 'account/login.html')

    @staticmethod
    def post(request):
        return authenticate_user(request)


class LogoutUser(View):

    @staticmethod
    def get(request):
        logout(request)
        return HttpResponseRedirect('/login/')


class JournalTreeView(AuthenticatedMixin):

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


class PermissionUser(AuthenticatedMixin):

    @staticmethod
    def post(request, **kwargs):
        tree = Tree.objects.get(slug=kwargs['tree'])
        user = User.objects.get(username=request.POST.get('login').split(' ')[0])
        tree.user.add(user)
        messages.success(request, 'Пользователь @{} допущен к дереву "{}"'.format(user, tree))
        return HttpResponseRedirect(tree.get_absolute_url('journal_tree'))


class TerminationAccess(AuthenticatedMixin):

    @staticmethod
    def get(request, **kwargs):
        tree = Tree.objects.get(slug=kwargs['tree'])
        user = User.objects.get(username=kwargs['username'])
        tree.user.remove(user)
        messages.error(request, 'Доступ @{} к дереву "{}" прекращен'.format(user, tree))
        return HttpResponseRedirect(tree.get_absolute_url('journal_tree'))


class DeletePhotoHuman(AuthenticatedMixin):

    @staticmethod
    def get(request, **kwargs):
        human = Human.objects.get(tree=Tree.objects.get(user=request.user, slug=kwargs['tree']), slug=kwargs['slug'])
        human.image = None
        human.save()
        messages.error(request, 'Фото человека {} удалено из дерева "{}"'.format(human, human.tree))
        return HttpResponseRedirect(human.get_absolute_url())
