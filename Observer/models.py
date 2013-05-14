from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin
import json

class Status(models.Model):
    class Meta:
        verbose_name_plural = 'Statuses'
    id = models.BigIntegerField(primary_key=True)
    content = models.TextField()
    
    def content_summary(self):
        return json.loads(self.content).get('text', '(Empty)')[:32]
    content_summary.short_description= 'Content'

    def __unicode__(self): # displayed in other's ForeignKey field.
        return str(self.id)

class WeiboAccount(models.Model):
    user = models.OneToOneField(User)
    weibo_id = models.BigIntegerField()
    access_token = models.CharField(max_length=48)
    expiry_time = models.DateTimeField(auto_now_add=False, auto_now=False)
    latest_status = models.ForeignKey(Status, blank=True, null=True)
    last_crawled = models.DateTimeField(auto_now=True)
    
    def __unicode__(self): # displayed in other's ForeignKey field.
        return str(self.weibo_id)
    
class History(models.Model):
    class Meta:
        verbose_name_plural = 'Histories'
    user = models.ForeignKey(WeiboAccount)
    status = models.ForeignKey(Status)
    rewteeted_status = models.ForeignKey(Status, related_name='retweeted_by', null=True)
    
    def WeiboId(self):
        return self.user.weibo_id
    WeiboId.short_description = 'User ID'
    def StatusId(self):
        return self.status.id
    StatusId.short_description = 'Status ID'
    def StatusContent(self):
        return self.status.content_summary()
    StatusContent.short_description = 'Status Content'
    def RetweetId(self):
        if self.rewteeted_status:
            return str(self.rewteeted_status.id)
        else:
            return '(None)'
    RetweetId.short_description = 'Retweeted Status'

    def __unicode__(self): # displayed in other's ForeignKey field.
        return str(self.user)
    
class WeiboUser(models.Model):
    id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=64)
    avatar = models.CharField(max_length=64)
    details = models.TextField()
    
    
    

class StatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'content_summary')

    
class WeiboAccountAdmin(admin.ModelAdmin):
    list_display = ('weibo_id', 'expiry_time', 'last_crawled')

    
class HistoryAdmin(admin.ModelAdmin):
    list_display = ('WeiboId', 'StatusId', 'StatusContent', 'RetweetId')
    
class WeiboUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    
admin.site.register(Status, StatusAdmin)
admin.site.register(WeiboAccount, WeiboAccountAdmin)
admin.site.register(History, HistoryAdmin)
admin.site.register(WeiboUser, WeiboUserAdmin)

