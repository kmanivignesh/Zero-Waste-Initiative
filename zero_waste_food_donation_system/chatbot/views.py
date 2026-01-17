from django.shortcuts import render
from django.http import JsonResponse
from .utils import explain_priority

def chatbot_page(request):
    return render(request, "chatbot/chatbot.html")

import re
from django.http import JsonResponse
from .utils import explain_priority

def chatbot_response(request):
    message = request.GET.get("message", "").lower()

    # Extract donation ID using regex
    match = re.search(r'donation\s*(\d+)', message)

    if match:
        donation_id = int(match.group(1))
        reply = explain_priority(donation_id)
    else:
        reply = (
            "I can explain donation priority. "
            "Try: 'Why is donation 3 high priority?'"
        )

    return JsonResponse({"reply": reply})

