from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test, REDIRECT_FIELD_NAME
from django.http import HttpResponse, HttpResponseRedirect
from django.db import transaction
from django.utils.timezone import now
from models import WeiboAccount
import weibo
from datetime import timedelta

def weibo_login_check(user):
    if not user.is_authenticated():
        user.client = None
        return False
    client = weibo.APIClient(app_key=settings.WEIBO_APPKEY, app_secret=settings.WEIBO_APPSECRET)
    client.set_access_token(user.get_profile().access_token, 0)
    user.client = client
    return True
    
def weibo_loggedin(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    actual_decorator = user_passes_test(
        weibo_login_check,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


@weibo_loggedin
def user_logout(request):
    logout(request)
    return HttpResponseRedirect('/')

def user_login(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(request.GET.get('next', '/'))
    else:
        code = request.GET.get('code', None)
        callback_uri = request.build_absolute_uri()
        callback_uri = callback_uri.split('?')[0] # Remove GET parameters
        callback_uri = "https:" + callback_uri.partition(':')[2] # Force HTTPS
        client = weibo.APIClient(app_key=settings.WEIBO_APPKEY, app_secret=settings.WEIBO_APPSECRET, 
            redirect_uri=callback_uri)
        if code: # Third leg of OAuth, check against server
            try:
                r = client.request_access_token(code)
            except weibo.APIError as e:
                return HttpResponse(str(e))
            
            access_token = r.access_token 
            expires_in = r.expires_in
            uid = r.uid
            try:
                user = User.objects.get(username=uid)
            except User.DoesNotExist:
                user = User.objects.create_user(uid)
                
            if int(uid) in settings.WEIBO_ADMINS and (not user.is_superuser):
                user.is_staff = True
                user.is_superuser = True
                user.save()
                
            try:
                profile = user.get_profile()
            except WeiboAccount.DoesNotExist:
                profile = WeiboAccount()
                profile.user = user
                profile.weibo_id = int(uid)
            profile.access_token  = access_token
            profile.expiry_time = now() + timedelta(seconds = expires_in)
            profile.save()
            ## Login successfully, note the hack of 'backend' here
            user.backend = settings.AUTHENTICATION_BACKENDS[0]
            login(request, user) 
            
            return HttpResponseRedirect(request.GET.get('next', '/'))
        # Fall over: either no cod is provided, or OAuth failed, 
        # Perform first leg of OAuth
        return HttpResponseRedirect(client.get_authorize_url()) 
    
