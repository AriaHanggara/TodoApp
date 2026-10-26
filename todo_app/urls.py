from django.urls import path
from . import views
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

app_name='todo_app'
urlpatterns = [
	path('login/', views.CustomLoginView.as_view(), name='login'),
	path('logout/', views.logout_view, name='logout'),

	path('client-autocomplete/', views.ClientFormAutocomplete.as_view(), name='autocomplete_client'),
	path('contract-autocomplete/', views.ContractFormAutocomplete.as_view(), name='autocomplete_contract'),

	path('client/', views.ListClientView.as_view(), name='client_list'),
	path('create-client/', views.CreateClientView.as_view(), name='client_create'),
	path('edit-client/<int:pk>/', views.EditClientView.as_view(), name='client_edit'),
	path("delete-client/<int:pk>/", views.DeleteClientView.as_view(), name='client_delete'),
	path('search-client/', views.SearchClientView.as_view(), name='search_client'),

	path('contract/', views.ListContractView.as_view(), name='contract_list'),
	path('create-contract/', views.CreateContractView.as_view(), name='contract_create'),
	path('edit-contract/<int:pk>/', views.EditContractView.as_view(), name='contract_edit'),
	path("delete-contract/<int:pk>/", views.DeleteContractView.as_view(), name='contract_delete'),
	path('search-contract/', views.SearchContractView.as_view(), name='search_contract'),

	path('payment/', views.ListPaymentView.as_view(), name='payment_list'),
	path('create-payment/', views.CreatePaymentView.as_view(), name='payment_create'),
	path('edit-payment/<int:pk>/', views.EditPaymentView.as_view(), name='payment_edit'),
	path("delete-payment/<int:pk>/", views.DeletePaymentView.as_view(), name='payment_delete'),
	path('search-payment/', views.SearchPaymentView.as_view(), name='search_payment'),


	path('', views.ListTeachingView.as_view(), name='teaching_list'),
	path('create-teaching/', views.CreateTeachingView.as_view(), name='teaching_create'),
	path("delete-teaching/<int:pk>/", views.DeleteTeachingView.as_view(), name='teaching_delete'),
	path('edit-teaching/<int:pk>/', views.EditTeachingView.as_view(), name='teaching_edit'),
	path('search-teaching/', views.SearchTeachingView.as_view(), name='search_teaching'),
	path('record-teaching/<int:pk>/', views.RecordTeachingView.as_view(), name='teaching_record'), ## url buat add record di modal
	path('record-teaching/', views.ListTeachingRecordView.as_view(), name='teaching_record_list'),
	path("delete-teaching-record/<int:pk>/", views.DeleteTeachingRecordView.as_view(), name='teaching_record_delete'),
	path('search-teaching-record/', views.SearchTeachingRecordView.as_view(), name='search_teaching_record'),

	path('about-me/', views.AboutView.as_view(), name='about_me'),
]



if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)