from django.shortcuts import get_object_or_404, render_to_response
from userapp.models import Page

def page_detail(request, page_id):
    page = get_object_or_404(Page, id=page_id)
    return render_to_response('userapp/page_detail.html', {'page': page})
