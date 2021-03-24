from django.http import HttpResponseRedirect
from django.views.generic import View
from django.shortcuts import render
from django.urls import reverse
from .models import Tree, User, Message


class AuthenticatedMixin(View):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_active:
            return HttpResponseRedirect('/login/')
        else:
            user_trees = Tree.objects.filter(creator=request.user)
            change_user_trees = Tree.objects.filter(user=request.user)
            list_change_user_trees = []
            for tree in change_user_trees:
                if tree.creator != request.user:
                    list_change_user_trees.append(tree)
            self.context = {
                'auth_user': request.user,
                'user_info': reverse('user_info', kwargs={'username': request.user.username}),
                'number_unread_messages': Message.get_number_unread_messages(request.user),
                'auth_user_all_trees': change_user_trees,
                'auth_user_change_trees': list_change_user_trees,
                'auth_user_trees': user_trees
            }
            return super(AuthenticatedMixin, self).dispatch(request, *args, **kwargs)


class VerificationAccessTreeMixin(View):

    def dispatch(self, request, *args, **kwargs):
        if 'tree' in kwargs:
            if self.context['auth_user_all_trees'].filter(slug=kwargs['tree']).exists():
                return super(VerificationAccessTreeMixin, self).dispatch(request, *args, **kwargs)
        else:
            if (not request.user.first_name) or request.user.username == kwargs['username']:
                return super(VerificationAccessTreeMixin, self).dispatch(request, *args, **kwargs)
            stranger = User.objects.get(username=kwargs['username'])
            stranger_trees = Tree.objects.filter(user=stranger) & self.context['auth_user_all_trees']
            if stranger_trees.exists():
                return super(VerificationAccessTreeMixin, self).dispatch(request, *args, **kwargs)
        self.context.update({
            'title': 'Чужие родственники Вам не доступны | Родословная',
            'tree_slug': kwargs['tree']
        })
        return render(request, 'account/no_access.html', self.context)
