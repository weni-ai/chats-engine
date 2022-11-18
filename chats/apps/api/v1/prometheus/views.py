from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from django.http import HttpResponse

from django.conf import settings

def metrics_view(request):
    try:
        authentication_token = settings.PROMETHEUS_AUTH_TOKEN
        header = request.META.get('HTTP_AUTHORIZATION', None)
        token = header.split()[1]
        if authentication_token == token:  
            return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
        else:
            return HttpResponse("Detail: You dont have permission to access metrics", status=401)
    except AttributeError:
        return HttpResponse("Detail: You dont have permission to access metrics", status=401)
    
