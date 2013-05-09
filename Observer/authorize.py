from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.db import transaction
from models import WeiboAccount
import weibo
import datetime


@login_required
def user_logout(request):
    logout(request)
    return HttpResponseRedirect('/')

@transaction.commit_on_success
def user_login(request):
    if request.user.is_authenticated():
        pass # Do nothing
    else:
        code = request.GET.get('code', None)
        client = weibo.APIClient(app_key=settings.WEIBO_APPKEY, app_secret=settings.WEIBO_APPSECRET, 
            redirect_uri=request.build_absolute_uri().split('?')[0])
        if code: # Third leg of OAuth, check against server
            try:
                r = client.request_access_token(code)
            except weibo.APIError as e:
                return HttpResponse(str(e))
            
            access_token = r.access_token 
            expires = r.expires
            uid = r.uid
            try:
                user = User.objects.get(username=uid)
            except User.DoesNotExist:
                user = User.objects.create_user(uid)
            
            try:
                profile = user.get_profile()
            except WeiboAccount.DoesNotExist:
                profile = WeiboAccount()
                profile.user = user
                profile.weibo_id = int(uid)
            profile.access_token  = access_token
            profile.expiry_time = datetime.datetime.fromtimestamp(expires)
            profile.save()
            ## Login successfully, note the hack of 'backend' here
            user.backend = settings.AUTHENTICATION_BACKENDS[0]
            login(request, user) 
            
            return HttpResponseRedirect(request.GET.get('next', '/'))
        # Fall over: either no cod is provided, or OAuth failed, 
        # Perform first leg of OAuth
        return HttpResponseRedirect(client.get_authorize_url()) 
    
