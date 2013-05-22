'''
Created on 19 May 2013

@author: Rubin
'''
from django.http import HttpResponse, HttpResponseBadRequest
from authorize import weibo_loggedin
import json
from models import Status



@weibo_loggedin
def history(request):
    try:
        min_id = int(request.GET.get('min', None))
        max_id = int(request.GET.get('max', None))
    except ValueError:
        return HttpResponseBadRequest()
        
    if (not min_id) or (not max_id) or (min_id > max_id):
        return HttpResponseBadRequest()

    result = request.user.get_profile().statuses.filter(id__gte=min_id,id__lte=max_id).order_by('id')
    result_ids = map(lambda x : x.id, result )
    return HttpResponse(json.dumps(result_ids), mimetype="application/json")


def reassemble_status(status):
    """
    database -> json status dict with retweet
    """
    status_dict = status.get_content()
    if status.retweet:
        status_dict.retweeted_status = status.retweet.get_content()
    return status_dict


@weibo_loggedin
def retrieve(request):
    try:
        status_id = int(request.GET.get('id', None))
    except ValueError:
        return HttpResponseBadRequest()
    if not status_id:
        return HttpResponseBadRequest()

    ## Permission check
    try:
        status = request.user.get_profile().statuses.filter(id=status_id).get()
        return HttpResponse(json.dumps(reassemble_status(status)), mimetype="application/json")
    except Status.DoesNotExist:
        return HttpResponseBadRequest()
    

