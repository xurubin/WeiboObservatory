from django.http import HttpResponse 
import json
from authorize import weibo_loggedin

@weibo_loggedin
def main(request):
    
    return HttpResponse(json.dumps(request.user.client.account.rate_limit_status.get(), indent=4), mimetype='text/plain')
