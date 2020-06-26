from django.contrib import admin
from .models import Session
from .models import Subject


# Register your models here.
admin.register(Session, site='ImageSearcher')
admin.register(Subject, site='ImageSearcher')
