from django.conf import settings
from django.http import HttpResponse
from django.db import transaction
import weibo
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Q
from persistence import store_status
from models import WeiboAccount, History

#TODO: limit to internal cron scheduler
def crawl(request):
    result = []
    crawl_cutoff = now() - timedelta(minutes = 6)
    for account in WeiboAccount.objects.filter(
                Q(expiry_time__gt=now()), 
                Q(last_crawled__lt=crawl_cutoff) | Q(latest_status__isnull=True)):
        tweets = crawl_user(account)
        result.append('User %d' % account.weibo_id)
        result.extend(map(str, tweets))
        
    return HttpResponse('\n'.join(result), mimetype='text/plain')

##@transaction.commit_on_success
def crawl_user(account):
    client = weibo.APIClient(app_key=settings.WEIBO_APPKEY, app_secret=settings.WEIBO_APPSECRET)
    client.set_access_token(account.access_token, 0)
    
    if settings.DEBUG:
        COUNT = 10
    else:
        COUNT = 100
    ##TODO: handle exception
    if account.latest_status:
        statuses = client.statuses.home_timeline.get(since_id = account.latest_status.id, count = COUNT).statuses
    else:
        statuses = client.statuses.home_timeline.get(count = COUNT).statuses
    
    result = []
    statuses.sort(key=lambda s:s.id)
    
    saved_statuses = map(store_status, statuses)
    for status, retweet in saved_statuses:
        h = History()
        h.user = account
        h.status = status
        h.rewteeted_status = retweet
        h.save()
        result.append(status.id)
    if saved_statuses:
        account.latest_status = saved_statuses[-1][0]
    account.save()
    return result
    
