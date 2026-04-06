from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('overview/', views.overview, name='overview'),
    path('signin/', views.signin, name='signin'),
    path('get-started/', views.register, name='register'),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("logout/", views.logout_view, name="logout"),
    path("history/", views.history, name="history"),
    path("habits/", views.habits, name="habits"),
    path("charts/", views.charts, name="charts"),
    path("streaks/", views.streaks, name="streaks"),
    path("mark-complete/<int:habit_id>/", views.mark_complete, name="mark_complete"),


]
