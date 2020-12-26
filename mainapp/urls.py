from .views import *

from django.urls import path

urlpatterns = [
    path('tree/<str:tree>/', BaseTreeView.as_view(), name='tree'),
    path('people/<str:tree>/<str:slug>/', HumanDetailView.as_view(), name='human_detail'),
    path('search_result/', SearchResultView.as_view(), name='search_result'),
    path('change_info_human/<str:tree>/<str:slug>/', ChangeHumanDetailView.as_view(), name='change_info_human'),
    path('save_human/<str:tree>/<str:slug>/', SaveHuman.as_view(), name='save_human'),
    path('delete_human/<str:tree>/<str:slug>/', DeleteHuman.as_view(), name='delete_human'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('user_info/<str:username>/', UserInfoView.as_view(), name='user_info'),
    path('change_info_user/<str:username>/', ChangeUserInfoView.as_view(), name='change_info_user'),
    path('delete_user/<str:username>/', DeleteUser.as_view(), name='delete_user'),
    path('redirection/', RedirectionBase.as_view(), name='redirection'),
    path('delete_tree/<str:tree>/', DeleteTree.as_view(), name='delete_tree'),
    path('login/', LoginUser.as_view(), name='login'),
    path('logout/', LogoutUser.as_view(), name='logout'),
    path('journal_tree/<str:tree>/', JournalTreeView.as_view(), name='journal_tree'),
    path('permission_user/<str:tree>/', PermissionUser.as_view(), name='permission_user'),
    path('termination_access/<str:tree>/<str:username>/', TerminationAccess.as_view(), name='termination_access'),
    path('delete_photo_human/<str:tree>/<str:slug>/', DeletePhotoHuman.as_view(), name='delete_photo_human')
]
