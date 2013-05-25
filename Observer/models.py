from django.db import models
from django.contrib.auth.models import User
import json
from django.core import urlresolvers
from weibo import JsonDict
import hashlib
import struct

class Status(models.Model):
    NOT_DELETED     = 0
    CONTENT_HIDDEN  = 1
    DELETED_FULL    = 2
    RETWEET_HIDDEN  = 3
    RETWEET_DELETED = 4
    
    class Meta:
        verbose_name_plural = 'Statuses'
        
    id = models.BigIntegerField(primary_key=True)
    content = models.TextField()
    retweet = models.ForeignKey('self', blank=True, null=True)
    deleted = models.SmallIntegerField(default=NOT_DELETED, choices = (
                                           (NOT_DELETED, 'Not deleted'),
                                           (CONTENT_HIDDEN, 'Content hidden'),
                                           (DELETED_FULL, 'Fully deleted'),
                                           (RETWEET_HIDDEN, 'Rewteet hidden'),
                                           (RETWEET_DELETED, 'Retweet deleted')))
    deleted_at = models.DateTimeField(blank=True, null=True)
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
            if self.content_dict.get('deleted', False): # Deleted status only has limited fields (deleted, text, created_at(null), id)
                self.content_dict.user = None
            else:
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
        return self.deleted == Status.NOT_DELETED
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
    weibo_name = models.CharField(max_length=48)
    weibo_avatar = models.CharField(max_length=64)
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
    



