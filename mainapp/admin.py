from django.contrib import admin
from .models import *

admin.site.register(Human)
admin.site.register(Tree)
admin.site.register(Message)
admin.site.register(NumberChanges)