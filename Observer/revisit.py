from django.conf import settings
from django.http import HttpResponse
from django.db import transaction
import weibo
from django.utils.timezone import now
from django.db.models import Q
from models import WeiboAccount, Status
from datetime import datetime

def revisit(request):
    target_accounts = WeiboAccount.objects.filter(
                Q(expiry_time__gt=now()), 
                Q(latest_status__isnull=False))
    
    ## Priority queue?
    logs = dict([(acc, ["User %d" % acc.weibo_id]) for acc in target_accounts])
    accounts = dict([(acc, acc.latest_status.id) for acc in target_accounts])
    for _ in range(5): # Number of iterations should depend on API quota.
        ## Always process the account with the latest unvisited status
        ## This will help exploring the status space roughly in accordance 
        ## to time progression.
        if not accounts: break
        acc = max(accounts.iteritems(), key=lambda x:x[1])
        account = acc[0]
        latest_sid = acc[1]
        new_latest_sid = revisit_user(account, latest_sid, logs[account])
        if new_latest_sid:
            assert new_latest_sid < latest_sid
            accounts[account] = new_latest_sid
        else:
            del accounts[account]
        
    return HttpResponse('\n'.join(['\n'.join(log) for log in logs.itervalues()]), mimetype='text/plain')

## Mark status as deleted and update timestamp, if not marked before
def mark_deleted(status, type):
    if status.deleted != Status.NOT_DELETED:
        return
    status.deleted = type
    status.deleted_at = datetime.now()
    status.save()
    
    
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

    stored_statuses = list(weibo_account.statuses.defer('content').filter(
                       id__gte=visible_min_sid, id__lte=visible_max_sid).order_by('id'))
    
    
    ## Compare backwards i.e. from larger id to smaller id
    while visible_statuses or stored_statuses:
        if (not stored_statuses) or (visible_statuses[-1].id > stored_statuses[-1].id):
            not_crawled = visible_statuses.pop() ## JsonDict
            if not last_run:
                logs.append("%d(%s) missing in crawled history." % (not_crawled.id, not_crawled.created_at))
            else:
                not_crawled = None
                
        elif (not visible_statuses) or stored_statuses[-1].id > visible_statuses[-1].id:
            fully_deleted = stored_statuses.pop() ## Status
            logs.append("%d(%s) completed deleted." % (fully_deleted.id, fully_deleted.get_content().created_at))
            mark_deleted(fully_deleted, Status.DELETED_FULL)
            
        else:
            s0 = visible_statuses.pop() ## JsonDict
            s1 = stored_statuses.pop() ## Status
            if not s1.cmp_content(s0.text):
                mark_deleted(s1, Status.CONTENT_HIDDEN)
                logs.append("%d(%s) content hidden." % (s1.id, s1.get_content().created_at))
                
            elif s1.retweet and (not s1.retweet.cmp_content(s0.retweeted_status.text)):
                if s0.retweeted_status.text.find(u'\u4e0d\u9002\u5b9c') >= 0: # Not suitable (to publish)
                    # Mark retweet as hidden
                    mark_deleted(s1.retweet, Status.CONTENT_HIDDEN)
                    # Mark referers as rewteet_hidden
                    map(lambda s: mark_deleted(s, Status.RETWEET_HIDDEN), s1.retweet.status_set.all())
                    logs.append("%d(%s): %d retweet hidden." % (s1.id, s1.get_content().created_at, s1.retweet.id))
                else: ## Author deleted the retweet
                    mark_deleted(s1.retweet, Status.DELETED_FULL)
                    map(lambda s: mark_deleted(s, Status.RETWEET_DELETED), s1.retweet.status_set.all())
                    logs.append("%d(%s): %d retweet deleted." % (s1.id, s1.get_content().created_at, s1.retweet.id))
                    
            else:
                logs.append("%d(%s) unchanged." % (s1.id, s1.get_content().created_at))
    
    if last_run:
        logs.append("EOF")
        return None ## We have reached the end of local history, no need to revisit next time
    else:
        logs.append("--------")
        return visible_min_sid - 1
