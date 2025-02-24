from django.urls import path
from credit.views import settings, credit

app_name="credit"

urlpatterns = [ 


    path("credit-settings/", settings.credit_settings, name="credit_settings"),
    path('credit-committee/remove/<int:member_id>/', settings.remove_credit_committee_member, name='remove_credit_committee_member'),


    path('create_credit_application/', credit.create_credit_application, name='create_credit_application'),
    path('credit_application/<int:credit_id>/', credit.credit_application_detail, name='credit_application_detail'),  # Optional detail view

]



