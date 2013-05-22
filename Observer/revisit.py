from django.conf import settings
from django.http import HttpResponse
from django.db import transaction
import weibo
from django.utils.timezone import now
from django.db.models import Q
from models import WeiboAccount


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
        if not accounts: break
        acc = max(accounts.iteritems(), key=lambda x:x[1])
        account = acc[0]
        latest_sid = acc[1]
        new_latest_sid = revisit_user(account, latest_sid, logs)
        if new_latest_sid:
            assert new_latest_sid < latest_sid
            accounts[account] = new_latest_sid
        else:
            del accounts[account]
        
    return HttpResponse('\n'.join(logs), mimetype='text/plain')


def revisit_user(weibo_account, max_status_id, logs):
    client = weibo.APIClient(app_key=settings.WEIBO_APPKEY, app_secret=settings.WEIBO_APPSECRET)
    client.set_access_token(weibo_account.access_token, 0)
    COUNT = settings.WEIBO_API_MAX_COUNT
    
    visible_statuses = sorted(client.statuses.home_timeline.get(
                                    max_id = max_status_id, count = COUNT, trim_user = 1).statuses,
                              key = lambda x: x.id)
    
    if not visible_statuses:
        return None
    
    visible_min_sid = min(visible_statuses, key=lambda x:x.id).id
    visible_max_sid = max(visible_statuses, key=lambda x:x.id).id
    
    ## Have we reached the end of local stored history?
    last_run = not weibo_account.statuses.filter(id__lt=visible_min_sid).exists()

    stored_statuses = list(weibo_account.statuses.filter(
                       id__gte=visible_min_sid, id__lte=visible_max_sid).order_by('id'))
    
    
    ## Compare backwards i.e. from larger id to smaller id
    while visible_statuses or stored_statuses:
        if (not stored_statuses) or (visible_statuses[-1].id > stored_statuses[-1].id):
            not_crawled = visible_statuses.pop() ## JsonDict
            if not last_run:
                logs.append("Status %d missing in crawled history." % not_crawled.id)
            else:
                not_crawled = None
                
        elif (not visible_statuses) or stored_statuses[-1].id > visible_statuses[-1].id:
            fully_deleted = stored_statuses.pop() ## Status
            logs.append("Status %d completed deleted." % fully_deleted.id)
            
        else:
            s0 = visible_statuses.pop()
            s1 = stored_statuses.pop()
            content_deleted = None
            if not s1.cmp_content(s0.text):
                content_deleted = s1 ## Status
                logs.append("Status %d content hidden." % content_deleted.id)
            elif s1.retweet and (not s1.retweet.cmp_content(s0.retweeted_status.text)):
                content_deleted = s1.retweet ## Status/retweeted
                logs.append("Status %d(%d) retweet hidden." % (s1.id, content_deleted.id))
                
            if (not content_deleted) and settings.DEBUG:
                logs.append("Status %d unchanged." % s1.id)
    
    if last_run:
        return None ## We have reached the end of local history, no need to revisit next time
    else:
        return visible_min_sid - 1
