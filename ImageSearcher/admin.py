from django.contrib import admin
from dicoms.models import Subject
from dicoms.models import Session
from dicoms.models import Series
from dicoms.models import Search

admin.site.register(Session)
admin.site.register(Subject)
admin.site.register(Series)
admin.site.register(Search)
