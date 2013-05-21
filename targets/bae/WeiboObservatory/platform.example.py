## Platform-specific settings.
from bae.core import const

DEBUG = False
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '??',                     
        'USER': const.MYSQL_USER,                    
        'PASSWORD': const.MYSQL_PASS,                 
        'HOST': const.MYSQL_HOST,                      
        'PORT': const.MYSQL_PORT,                     
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.bcms.EmailBackend'
EMAIL_BCMS_QNAME = '??'

WEIBO_APPKEY = '??'
WEIBO_APPSECRET = '??'

"""
Monkey patch BAE's email backend such that sent html_message can go through.
Mainly used for sending HTML traceback. 
"""
import django.core.mail
real_mail_admins = django.core.mail.mail_admins
def mail_admins_delegate(subject, message, fail_silently=False, connection=None,
                html_message=None):
    if html_message:
        message = '<!--HTML-->\n%s<p>%s' %(html_message, message) 
        html_message = None
    real_mail_admins(subject, message, fail_silently, connection, html_message)
django.core.mail.mail_admins = mail_admins_delegate

    