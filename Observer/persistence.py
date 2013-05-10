from models import Status, WeiboUser
import json

def store_status(status_dict):
    """
    json status dict with retweet -> database.
    returns (Status, Status(retweet))
    """
    retweet = None
    try: ## Try to store retweets
        retweet = store_single_status(status_dict.retweeted_status)
        status_dict.retweeted_status = retweet.id
    except AttributeError:
        pass
        
    return store_single_status(status_dict), retweet

def store_single_status(status_dict):
    """
    json status dict -> database
    returns Status
    """
    try:
        s = Status.objects.get(id = status_dict.id)
    except Status.DoesNotExist:
        status_dict.user = store_user(status_dict.user).id
        
        s = Status()
        s.id = status_dict.id
        s.content = json.dumps(status_dict)
        s.save()
        
    return s

def load_status(status_id):
    """
    database -> json status dict with tweets
    """
    status = load_single_status(status_id)
    try: ## Try to load retweet
        status['retweeted_status'] = load_single_status(status['retweeted_status'])
    except KeyError:
        pass
    return status

def load_single_status(status_id):
    """
    database -> json status dict
    """
    status_obj = Status.objects.get(id=status_id)
    status = json.loads(status_obj.content)
    status['user'] = load_user(status['user'])
    return status
    
def store_user(user_dict):
    """
    json user dict -> database.
    """
    try:
        user = WeiboUser.objects.get(id = user_dict.id)
    except WeiboUser.DoesNotExist:
        user = WeiboUser()
        user.id = user_dict.id
        
    changed = False
    if user.name != user_dict.screen_name:
        user.name = user_dict.screen_name
        changed = True
    if user.avatar != user_dict.profile_image_url:
        user.avatar = user_dict.profile_image_url
        changed = True
    if changed:
        user.details = json.dumps(user_dict)
        user.save()
    return user

def load_user(user_id):
    return json.loads(WeiboUser.objects.get(id=user_id).details)
