from django.urls import include, path

urlpatterns = [
    path('', include('ciberbox.urls')),
    path('api/', include('ciberbox.urls_api')),
]
