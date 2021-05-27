from mainapp.models import Tree, NumberChanges, Message, User
from django.http import HttpResponseRedirect
from django.views.generic import View
from django.shortcuts import render
from django.urls import reverse


class AuthenticatedMixin(View):

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_active:
            return HttpResponseRedirect('/login/')
        else:
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
            self.context = {
                'auth_user': user,
                'user_info': reverse('user_info', kwargs={'username': user.username}),
                'number_unread_messages': Message.get_number_unread_messages(user),
                'auth_user_all_trees': change_user_trees,
                'auth_user_change_trees': get_dict_tree_and_unread_number(user, list_change_user_trees),
                'auth_user_trees': get_dict_tree_and_unread_number(user, user_trees)
            }
            return super(AuthenticatedMixin, self).dispatch(request, *args, **kwargs)


class VerificationAccessTreeMixin(View):

    def dispatch(self, request, *args, **kwargs):
        if 'tree' in kwargs:
            if self.context['auth_user_all_trees'].filter(slug=kwargs['tree']).exists():
                return super(VerificationAccessTreeMixin, self).dispatch(request, *args, **kwargs)
            tree = Tree.objects.get(slug=kwargs['tree'])
            self.context.update({
                'title': 'Чужие родственники Вам не доступны | Родословная',
                'tree_slug': kwargs['tree'],
                'check_request': request.user in tree.potential_user.all(),
                'tree': tree
            })
        else:
            if (not request.user.first_name) or request.user.username == kwargs['username']:
                return super(VerificationAccessTreeMixin, self).dispatch(request, *args, **kwargs)
            stranger = User.objects.get(username=kwargs['username'])
            stranger_trees = Tree.objects.filter(user=stranger) & self.context['auth_user_all_trees']
            if stranger_trees.exists():
                return super(VerificationAccessTreeMixin, self).dispatch(request, *args, **kwargs)
        self.context.update({
            'title': 'Чужие родственники Вам не доступны | Родословная'
        })
        return render(request, 'account/no_access.html', self.context)


def get_dict_tree_and_unread_number(user, qs):
    trees = {}
    for tree in qs:
        number = NumberChanges.objects.filter(user=user, tree=tree).first()
        trees[tree] = number.number if number else 0
    return trees
