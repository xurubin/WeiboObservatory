from django.http import HttpResponse
from django.shortcuts import render
from authorize import weibo_loggedin
from base62 import base62_encode
from models import Status
from django.db.models import Q

def call_command(name, *args, **options):
    """
    Shamelessly stolen from django.core.management.call_command
    """
    from django.core.management import load_command_class, NO_DEFAULT
    klass = load_command_class("django.core", name)

    defaults = {}
    for opt in klass.option_list:
        if opt.default is NO_DEFAULT:
            defaults[opt.dest] = None
        else:
            defaults[opt.dest] = opt.default
    defaults.update(options)

    from StringIO import StringIO 
    import sys
    content = StringIO()
    bak_out = sys.stdout
    sys.stdout = content
    klass.execute(*args, **defaults)
    sys.stdout = bak_out
    content.seek(0)
    return content.read()
    
def syncdb(request):
    ## BAE does not allow os.listdir(), which is required by django's call_command
    ## so we have to do it ourselves. Also, disable load_initial_data as it will lead
    ## to call_command() as well.
    result = call_command('syncdb', load_initial_data=False, interactive=False)

    return HttpResponse("syncdb\n" + result, mimetype='text/plain')

def to_mid(sid):
    result = []
    while sid:
        if sid < 10000000:
            result.insert(0, base62_encode(sid % 10000000))
        else:
            result.insert(0, base62_encode(sid % 10000000, padding=4))
        sid /= 10000000
    return "".join(result)

@weibo_loggedin
def home(request):
    profile = request.user.get_profile()
    all_statuses = profile.statuses
    PAGE_ITEMS = 20 
    
    ## Page navigation logic
    latest_id = int(request.GET.get('latest', 0))
    page = int(request.GET.get('page', 1))
    deleted = False
    if 'deleted' in request.GET:
        deleted = True
        all_statuses = all_statuses.filter(
                           Q(deleted = Status.CONTENT_HIDDEN) | 
                           Q(deleted = Status.DELETED_FULL) | 
                           Q(deleted = Status.RETWEET_HIDDEN) | 
                           Q(deleted = Status.RETWEET_DELETED))
        
    if latest_id:
        new_count = all_statuses.filter(id__gt=latest_id).count()
    else:
        try:
            latest_id = all_statuses.latest('id').id
        except Status.DoesNotExist:
            latest_id = 0
        new_count = 0
    
    known_statuses = all_statuses.filter(id__lte=latest_id).order_by('-id')
    page_count = (known_statuses.count() + PAGE_ITEMS - 1) / PAGE_ITEMS
    
    links = [('/?deleted' if deleted else '/', 
              'Latest' + (' (%d)' % new_count if new_count else ''))]
    
    for i in xrange(1, page_count):
        links.append(('/?latest=%d&page=%d%s' % (latest_id, i+1, '&deleted' if deleted else ''),
                      str(i+1)))
    
    ## Quota information
    if request.user.is_superuser:
        limits = request.user.client.account.rate_limit_status.get()
        quota = {'user_limit_percentage' : 100 * limits.remaining_user_hits / limits.user_limit,
                 'user_limit_tooltip' : '%d of %d remaining' % (limits.remaining_user_hits, limits.user_limit),
                 'ip_limit_percentage' : 100 * limits.remaining_ip_hits / limits.ip_limit,
                 'ip_limit_tooltip' : '%d of %d remaining' % (limits.remaining_ip_hits , limits.ip_limit),
                 }
    else:
        quota = {}
        
    ## User profile
    nickname = profile.weibo_name
    avatar = profile.weibo_avatar
    
    ## Status list
    statuses = []
    def to_template(status):
        s = status.get_content()
        if s.get('deleted', False):
            return { 'user'   : '',
                 'avatar' : '',
                 'text'   : s.text,
                 'images' : [],
                 'link'   : "#",
                 'time'   : '',
                } 
        images = []
        for image in s.pic_urls:
            thumb = image['thumbnail_pic']
            middle = image.get('bmiddle_pic', thumb.replace( 'thumbnail', 'bmiddle'))
            large = image.get('original_pic', thumb.replace( 'thumbnail', 'large'))
            images.append({'t' :thumb, 'm' : middle, 'l' : large})
        return { 'user'   : s.user.name,
                 'avatar' : s.user.profile_image_url,
                 'text'   : s.text,
                 'images' : images,
                 'link'   : "http://www.weibo.com/%d/%s" % (s.user.id, to_mid(s.id)),
                 'time'   : s.created_at,
                 'deleted': status.deleted == Status.CONTENT_HIDDEN or status.deleted == Status.DELETED_FULL,
                }
    for status in known_statuses[(page-1)*PAGE_ITEMS : page*PAGE_ITEMS]:
        template_data = [to_template(status)]
        if status.retweet:
            template_data.append(to_template(status.retweet))
            
        statuses.append(template_data)
        
    return render(request, 'home.html', {
                         'nickname': nickname,
                         'avatar' : avatar, 
                         'statuses' : statuses,
                         'links' : links,
                         'page' : page,
                         'quota' : quota
    })
