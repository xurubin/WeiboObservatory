'''
Created on 19 May 2013

@author: Rubin
'''
from django.http import HttpResponse, HttpResponseBadRequest
from authorize import weibo_loggedin
from models import History
from persistence import load_status
import json

@weibo_loggedin
def history(request):
    try:
        min_id = int(request.GET.get('min', None))
        max_id = int(request.GET.get('max', None))
    except ValueError:
        return HttpResponseBadRequest()
        
    if (not min_id) or (not max_id) or (min_id > max_id):
        return HttpResponseBadRequest()

    result = History.objects.filter(user=request.user.get_profile(), 
                           status_id__gte=min_id,
                           status_id__lte=max_id)
    result_ids = map(lambda x : x.status.id, result )
    return HttpResponse(json.dumps(result_ids), mimetype="application/json")


@weibo_loggedin
def retrieve(request):
    try:
        status_id = int(request.GET.get('id', None))
    except ValueError:
        return HttpResponseBadRequest()
    if not status_id:
        return HttpResponseBadRequest()

    ## Permission check
    if not History.objects.filter(user=request.user.get_profile(), status_id__exact=status_id).exists():
        return HttpResponseBadRequest()
    
    return HttpResponse(json.dumps(load_status(status_id)), mimetype="application/json")

