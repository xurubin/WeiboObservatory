from django.contrib import admin
from models import Status, WeiboAccount, History

class StatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'not_deleted', 'user_name', 'content_summary', 'RetweetId')

    
class WeiboAccountAdmin(admin.ModelAdmin):
    list_display = ('weibo_id', 'expiry_time', 'last_crawled')

    
class HistoryAdmin(admin.ModelAdmin):
    list_display = ('WeiboId', 'StatusId', 'StatusContent')

    
admin.site.register(Status, StatusAdmin)
admin.site.register(WeiboAccount, WeiboAccountAdmin)
admin.site.register(History, HistoryAdmin)
