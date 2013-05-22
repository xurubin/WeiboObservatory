from django.http import HttpResponse
from django.shortcuts import render
from authorize import weibo_loggedin
from persistence import load_status
from base62 import base62_encode

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

def to_mid(id):
    result = []
    while id:
        result.insert(0, base62_encode(id % 10000000))
        id /= 10000000
    return "".join(result)

@weibo_loggedin
def home(request):
    profile = request.user.get_profile()
    history = profile.history_set
    PAGE_ITEMS = 20 
    
    ## Page navigation logic
    latest = int(request.GET.get('latest', 0))
    page = int(request.GET.get('page', 1))
    if latest:
        new_count = history.filter(status_id__gt=latest).count()
    else:
        latest = history.order_by('-status__id')[0].status.id
        new_count = 0
    
    known_statuses = history.filter(status_id__lte=latest).order_by('-status__id')
    page_count = (known_statuses.count() + PAGE_ITEMS - 1) / PAGE_ITEMS
    
    links = [('/', 
              'Latest' + (' (%d)' % new_count if new_count else ''))]
    
    for i in xrange(1, page_count):
        links.append(('/?latest=%d&page=%d' % (latest, i+1),
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
    info = request.user.client.users.show.get(uid = profile.weibo_id)
    nickname = info.screen_name
    avatar = info.profile_image_url
    
    ## Status list
    statuses = []
    def to_template(s):
        images = []
        for image in s.pic_urls:
            thumb = image['thumbnail_pic']
            middle = image.get('bmiddle_pic', thumb.replace( 'thumbnail', 'bmiddle'))
            large = image.get('original_pic', thumb.replace( 'thumbnail', 'large'))
            images.append({'t' :thumb, 'm' : middle, 'l' : large})
        return { 'user' : s.user.screen_name,
                 'avatar' : s.user.profile_image_url,
                 'text' : s.text,
                 'images' : images,
                 'link' : "http://www.weibo.com/%d/%s" % (s.user.id, to_mid(s.id)),
                }
    for h in known_statuses[(page-1)*PAGE_ITEMS : page*PAGE_ITEMS]:
        status = load_status(h.status_id)
        template_data = [to_template(status) ]
        try:
            template_data.append(to_template(status.retweeted_status))
        except AttributeError:
            pass
            
        statuses.append(template_data)
        
    return render(request, 'home.html', {
                         'nickname': nickname,
                         'avatar' : avatar, 
                         'statuses' : statuses,
                         'links' : links,
                         'page' : page,
                         'quota' : quota
    })
