from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin
import json
from django.core import urlresolvers
from weibo import JsonDict
import hashlib
import struct

class Status(models.Model):
    class Meta:
        verbose_name_plural = 'Statuses'
        
    id = models.BigIntegerField(primary_key=True)
    content = models.TextField()
    retweet = models.ForeignKey('self', blank=True, null=True)
    deleted = models.BooleanField(default=False)
    content_hash = models.BigIntegerField(default=0)
    
    def set_content(self, data_dict):
        self.content = json.dumps(data_dict) # Compression here
        if hasattr(self, 'content_dict'):
            del self.content_dict
        if hasattr(self, 'user_dict'):
            del self.user_dict
        
    def get_content(self):
        if not hasattr(self, 'content_dict'):
            self.content_dict = JsonDict(json.loads(self.content)) # Decompression here
            self.content_dict.user = JsonDict(self.content_dict.user)
        return self.content_dict
    
    def _hash_content(self, text):
        return struct.unpack('<Q', hashlib.md5(text.encode('utf-8')).digest()[:8])[0]
    
    def cmp_content(self, text):
        if not self.content_hash:
            self.content_hash = self._hash_content(self.get_content().text)
            ## self.save()??
        return self.content_hash == self._hash_content(text)
    
    def _get_user(self):
        if not hasattr(self, 'user_dict'):
            self.user_dict = self.get_content().user
        return self.user_dict
        
    def content_text(self):
        return self.get_content().get('text', '(Empty)')
    
    def content_summary(self):
        return self.content_text()[:32]
    content_summary.short_description = 'Content'

    def not_deleted(self):
        return not self.deleted
    not_deleted.short_description = 'Existence'
    not_deleted.boolean = True
    
    def __unicode__(self): # displayed in other's ForeignKey field.
        return str(self.id)

    def RetweetId(self):
        if self.retweet:
            text = str(self.retweet.id)
            url = urlresolvers.reverse('admin:Observer_status_change', args=(self.retweet.id,))
        else:
            text = '(None)'
            url = '#'
        return '<a href="%s">%s</a>' % (url, text)
    RetweetId.short_description = 'Retweeted Status'
    RetweetId.allow_tags = True
    
    def user_name(self):
        return self._get_user().name
    user_name.short_description = 'User'
    
    
class WeiboAccount(models.Model):
    user = models.OneToOneField(User)
    weibo_id = models.BigIntegerField()
    access_token = models.CharField(max_length=48)
    expiry_time = models.DateTimeField(auto_now_add=False, auto_now=False)
    latest_status = models.ForeignKey(Status, blank=True, null=True, related_name='+')
    last_crawled = models.DateTimeField(auto_now=True)
    statuses = models.ManyToManyField(Status, through = 'History')
    
    def __unicode__(self): # displayed in other's ForeignKey field.
        return str(self.weibo_id)
    
class History(models.Model):
    class Meta:
        verbose_name_plural = 'Histories'
    user = models.ForeignKey(WeiboAccount)
    status = models.ForeignKey(Status)
    
    def WeiboId(self):
        return self.user.weibo_id
    WeiboId.short_description = 'User ID'
    def StatusId(self):
        sid = self.status.id
        url = urlresolvers.reverse('admin:Observer_status_change', args=(sid,))
        return '<a href="%s">%d</a>' % (url, sid)
    StatusId.short_description = 'Status ID'
    StatusId.allow_tags = True
    
    def StatusContent(self):
        return self.status.content_summary()
    StatusContent.short_description = 'Status Content'
        
    def __unicode__(self): # displayed in other's ForeignKey field.
        return str(self.user)
    


class StatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'not_deleted', 'user_name', 'content_summary', 'RetweetId')

    
class WeiboAccountAdmin(admin.ModelAdmin):
    list_display = ('weibo_id', 'expiry_time', 'last_crawled')

    
class HistoryAdmin(admin.ModelAdmin):
    list_display = ('WeiboId', 'StatusId', 'StatusContent')

    
admin.site.register(Status, StatusAdmin)
admin.site.register(WeiboAccount, WeiboAccountAdmin)
admin.site.register(History, HistoryAdmin)

