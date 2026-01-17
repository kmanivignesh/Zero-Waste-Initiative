from django.urls import path
from .views import chatbot_page, chatbot_response

urlpatterns = [
    path("", chatbot_page, name="chatbot"),
    path("reply/", chatbot_response, name="chatbot_reply"),
]
