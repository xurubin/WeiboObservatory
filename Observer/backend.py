from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.db import transaction
import weibo
from models import Status, History, WeiboAccount
from datetime import datetime, timedelta
import json
from django.db.models import Q

#TODO: limit to internal cron scheduler
def crawl(request):
    result = []
    crawl_cutoff = datetime.now() - timedelta(minutes = 6)
    for account in WeiboAccount.objects.filter(
                Q(expiry_time__gt=datetime.now()), 
                Q(last_crawled__lt=crawl_cutoff) | Q(last_crawled__isnull=True)):
        tweets = crawl_user(account)
        result.append('User %d' % account.weibo_id)
        result.extend(map(str, tweets))
        
    return HttpResponse('\n'.join(result), mimetype='text/plain')

##@transaction.commit_on_success
def crawl_user(account):
    client = weibo.APIClient(app_key=settings.WEIBO_APPKEY, app_secret=settings.WEIBO_APPSECRET)
    client.set_access_token(account.access_token, 0)
    
    ##TODO: handle exception
    if account.latest_status:
        statuses = client.statuses.home_timeline.get(since_id = account.latest_status.id, count = 100, trim_user = 1).statuses
    else:
        statuses = client.statuses.home_timeline.get(count = 100, trim_user = 1).statuses
    
    result = []
    statuses.sort(key=lambda s:s.id)
    
    saved_statuses = map(store_status, statuses)
    for status, retweeted_status in saved_statuses:
        h = History()
        h.user = account
        h.status = status
        h.rewteeted_status = retweeted_status
        h.save()
        result.append(status.id)
    if saved_statuses:
        account.latest_status = saved_statuses[-1][0]
    account.save()
    return result
    
def store_status(status):
    try:
        retweet, _ = store_status(status.retweeted_status)
    except AttributeError:
        retweet = None
        
    try:
        s = Status.objects.get(id = status.id)
    except Status.DoesNotExist:
        s = Status()
        s.id = status.id
        s.content = json.dumps(status)
        s.save()
        
    return s, retweet
