from django.conf import settings
from django.http import HttpResponse
from django.db import transaction
import weibo
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Q
from persistence import store_status
from models import WeiboAccount, History

##TODO: limit to internal cron scheduler
##TODO: partition space for concurrent crawling
def crawl(request):
    result = []
    crawl_cutoff = now() - timedelta(minutes = 4)
    for account in WeiboAccount.objects.filter(
                Q(expiry_time__gt=now()), 
                Q(last_crawled__lt=crawl_cutoff) | Q(latest_status__isnull=True)):
        tweets = crawl_user(account)
        result.append('User %d' % account.weibo_id)
        result.extend(map(str, tweets))
        
    return HttpResponse('\n'.join(result), mimetype='text/plain')

@transaction.commit_on_success
def crawl_user(account):
    client = weibo.APIClient(app_key=settings.WEIBO_APPKEY, app_secret=settings.WEIBO_APPSECRET)
    client.set_access_token(account.access_token, 0)
    
    if settings.DEBUG:
        COUNT = 10
    else:
        COUNT = settings.WEIBO_API_MAX_COUNT
    ##TODO: handle exception
    if not account.latest_status:
        all_statuses = client.statuses.home_timeline.get(count = COUNT).statuses
    else:
        statuses = client.statuses.home_timeline.get(since_id = account.latest_status.id, count = COUNT).statuses
        all_statuses = statuses
        
        id_func = lambda s:s.id 
        while len(statuses) == COUNT:
            last_minid = min(map(id_func, statuses))
            ## The API will return the largest COUNT statuses whose id is larger than since_id
            ## so here is how we iterate to retrieve the entire set
            statuses = client.statuses.home_timeline.get(max_id = last_minid - 1, since_id = account.latest_status.id, count = COUNT).statuses
            all_statuses.extend(statuses)
            
    all_statuses.sort(key=id_func)
    ids = map(id_func, all_statuses)
    assert len(ids) == len(set(ids)) ## Sanity check: no duplicates in the list
    
    saved_statuses = map(store_status, all_statuses)
    for status, retweet in saved_statuses:
        h = History()
        h.user = account
        h.status = status
        h.rewteeted_status = retweet
        h.save()
    if saved_statuses:
        account.latest_status = saved_statuses[-1][0]
    account.save()
    return map(lambda s:s[0].id, saved_statuses)
    
def revisit(request):
    target_accounts = WeiboAccount.objects.filter(
                Q(expiry_time__gt=now()), 
                Q(latest_status__isnull=False))
    
    ## Priority queue?
    logs = []
    accounts = dict([(acc, acc.latest_status.id) for acc in target_accounts])
    for _ in range(1): # Number of iterations should depend on API quota.
        ## Always process the account with the latest unvisited status
        ## This will help exploring the status space roughly in accordance 
        ## to time progression.
        acc = max(accounts.iteritems(), lambda x:x[1])
        account = acc[0]
        latest_sid = acc[1]
        new_latest_sid = revisit_user(account, latest_sid, logs)
        assert new_latest_sid < latest_sid
        accounts[account] = new_latest_sid
        
    return HttpResponse('\n'.join(logs), mimetype='text/plain')


def revisit_user(weibo_account, max_status_id, logs):
    client = weibo.APIClient(app_key=settings.WEIBO_APPKEY, app_secret=settings.WEIBO_APPSECRET)
    client.set_access_token(weibo_account.access_token, 0)
    COUNT = settings.WEIBO_API_MAX_COUNT
    
    visible_statuses = client.statuses.home_timeline.get(since_id = max_status_id, count = COUNT, trim_user = 1).statuses
    visible_min_sid = min(visible_statuses, lambda x:x.id)
    visible_max_sid = max(visible_statuses, lambda x:x.id)
    stored_statuses = weibo_account.history_set.filter(
                       status_id__gte=visible_min_sid, status_id__lte=visible_max_sid).order_by('')
    
    return visible_min_sid - 1