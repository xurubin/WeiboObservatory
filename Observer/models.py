from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import User

class Status(models.Model):
    id = models.IntegerField(primary_key=True)
    content = models.TextField()
    
class WeiboAccount(models.Model):
    user = models.OneToOneField(User)
    weibo_id = models.IntegerField()
    access_token = models.CharField(max_length=48)
    expiry_time = models.DateTimeField(auto_now_add=False, auto_now=False)
    latest_status = models.ForeignKey(Status, null=True)
    last_crawled = models.DateTimeField(auto_now=True)
    
class History(models.Model):
    user = models.ForeignKey(WeiboAccount)
    status = models.ForeignKey(Status)
    rewteeted_status = models.ForeignKey(Status, related_name='retweeted_by', null=True)
    
