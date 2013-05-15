from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from authorize import weibo_loggedin
from models import History
from persistence import load_status
import json

def call_command(name, *args, **options):
    """
    Shamelessly stolen from django.core.management.call_command
    """
    from django.core.management import load_command_class, NO_DEFAULT
    klass = load_command_class("django.core", name)

    defaults = {}
    for opt in klass.option_list:
        if opt.default is NO_DEFAULT:
            defaults[opt.dest] = None
        else:
            defaults[opt.dest] = opt.default
    defaults.update(options)

    from StringIO import StringIO 
    import sys
    content = StringIO()
    bak_out = sys.stdout
    sys.stdout = content
    klass.execute(*args, **defaults)
    sys.stdout = bak_out
    content.seek(0)
    return content.read()
    
def syncdb(request):
    ## BAE does not allow os.listdir(), which is required by django's call_command
    ## so we have to do it ourselves. Also, disable load_initial_data as it will lead
    ## to call_command() as well.
    result = call_command('syncdb', load_initial_data=False, interactive=False)

    return HttpResponse("syncdb\n" + result, mimetype='text/plain')

@weibo_loggedin
def home(request):
    return render(request, 'home.html', {
                         'uid': str(request.user.client.account.get_uid.get().uid),
                         
    })

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

