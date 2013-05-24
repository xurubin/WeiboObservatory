from django.conf import settings
from django.http import HttpResponse
from django.db import transaction
import weibo
from django.utils.timezone import now
from datetime import timedelta, datetime
from django.db.models import Q
from models import WeiboAccount, History, Status

def store_status(status_dict):
    """
    json status dict with retweet -> database.
    returns Status
    """
    retweet = None
    if hasattr(status_dict, 'retweeted_status'):
        retweet = store_single_status(status_dict.retweeted_status, None)
        status_dict.pop('retweeted_status')
        
    return store_single_status(status_dict, retweet)

def store_single_status(status_dict, rewteet):
    """
    json status dict -> database
    returns Status
    """
    try:
        s = Status.objects.get(id = status_dict.id)
    except Status.DoesNotExist:
        s = Status()
        s.id = status_dict.id
        s.set_content(status_dict)
        s.retweet = rewteet
        s.save()
        
    return s

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

def older_than(time_str, delta_minutes):
    "Sat May 25 02:00:42 +0800 2013"
    _, month, day, time, tz, year = time_str.split(' ')
    local_time = datetime.strptime(' '.join([month, day, time, year]), '%b %d %H:%M:%S %Y')
    tz_diff = timedelta(hours = int(tz[1:3]), minutes = int(tz[3:5]))
    if tz[0] == '+':
        utc_time = local_time - tz_diff
    else:
        utc_time = local_time + tz_diff
        
    return utc_time <= datetime.utcnow() - timedelta(minutes = delta_minutes)
    
@transaction.commit_on_success
def crawl_user(account):
    client = weibo.APIClient(app_key=settings.WEIBO_APPKEY, app_secret=settings.WEIBO_APPSECRET)
    client.set_access_token(account.access_token, 0)
    
    if settings.DEBUG:
        COUNT = 21
    else:
        COUNT = settings.WEIBO_API_MAX_COUNT
    id_func = lambda s:s.id 
    
    ##TODO: handle exception
    if not account.latest_status:
        all_statuses = client.statuses.home_timeline.get(count = COUNT).statuses
    else:
        statuses = client.statuses.home_timeline.get(since_id = account.latest_status.id, count = COUNT).statuses
        all_statuses = statuses
        
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
    for status in saved_statuses:
        ## If we encounter duplicated status, do not create history m2m again
        if not status.weiboaccount_set.exists():
            h = History()
            h.user = account
            h.status = status
            h.save()
    ## Move on if we already have a few old statuses, or if they are quite old
    ## This is to deal with API sometimes having missing statuses in between (not even eventually consistent?!) 
    if saved_statuses and (len(saved_statuses) >= 5 or older_than(all_statuses[-1].created_at, 15)): 
        account.latest_status = saved_statuses[-1]
    account.save()
    return map(lambda s:s.id, saved_statuses)

