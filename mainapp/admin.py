from django.contrib import admin
from django.apps import apps
from .models import Routine

    
app_name = 'mainapp'

app_models = apps.get_app_config(app_name).get_models()

for model in app_models:
    admin.site.register(model)
    
    