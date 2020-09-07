from django.urls import path
from . import views

urlpatterns = [
    path("", views.gene_explorer, name="genes"),
]

app_name = "datasets"
