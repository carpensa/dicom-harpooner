from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.search_subjects, name='allsubjects'),
    path('search/', views.search_subjects, name='search'),
    path('search_results/', views.search_results, name='search_results'),
    path('search_selection/', views.search_selection, name='search_selection'),
    path('convert_builder/', views.convert_subjects, name='convert_builder'),
    path('convert/', views.convert, name='convert'),
    path('convert_builder/', views.create_dcm2bids_config, name='create_dcm2bids_config'),
]

# Here we launch our indexer
