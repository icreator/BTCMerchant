# -*- coding: utf-8 -*-
import os
from gluon.fileutils import read_file

response.generic_patterns = ['*.html']

no_img = SETS.no_img and request.is_local

response.logo = XML(SETS.logo)
response.sublogo = XML(SETS.sublogo)

##session.forget()
cache_expire = request.is_local and 3 or SETS.cache_expire

# переходник для показа ссыфлкок и картинок в листингах
def download():
    return response.download(request,db)

#@cache.action(time_expire=cache_expire, cache_model=cache.disk, quick='P')
def currs():
    #from applications.shop.modules.rates_lib import get_average_rate_bsa
    from db_common import get_currs_by_abbrev
    from rates_lib import get_average_rate_bsa
        
    ##session.forget(response)
    response.title = T('Used currencies')
    response.not_show_function = True


    #curr_out, x, e = get_currs_by_abbrev(db, 'RUB')
    h = CAT(
        TAG.center(H1(response.title)),
        H2(T('Crypto currencies'))
        )
    path = os.path.join(request.folder, 'static','images','currs')
    odd = None
    curr_out, x, e = get_currs_by_abbrev(db, 'USD')
    for rr in db((db.currs.used==True)
            & (db.currs.id==db.xcurrs.curr_id)).select(orderby=db.currs.name):

        b_rate, s_rate, avg_rate = get_average_rate_bsa(db, rr.currs.id, curr_out.id)

        # request.env.gluon_parent, 
        filename = os.path.join(path, rr.currs.abbrev + '.png')
        img_url = None
        if os.path.isfile(filename):
            img_url = URL('static','images/currs', args=[rr.currs.abbrev + '.png'])

        #img_url = URL('shop','default','download', args=[rr.currs.icon])
        img_url = img_url or rr.currs.icon and URL('default','download', args=[rr.currs.icon])
        h += DIV(
            DIV(
                IMG(_src=img_url, _width=40, _height=40, _class="lst_icon") if img_url else '',
                _class='col-sm-1',
            ),
            DIV(
                A(B(rr.currs.name), _href=rr.currs.url, _target='blank'), ' [', rr.currs.abbrev, '] ',
                SPAN(' ', B('Not used'), '. ') if not rr.currs.used else '',
                #P(rr.currs.desr,'. ', _class='small'),
                T('The average time to receive payment status'), ': ',
                'SOFT - %s sec; HARD - %s min; TRUE - %s min' % (rr.xcurrs.conf_soft*rr.xcurrs.block_time+10,
                                  round(rr.xcurrs.conf_hard*rr.xcurrs.block_time/60.0,2),
                                  round(rr.xcurrs.conf_true*rr.xcurrs.block_time/60.0,2)), '. ',BR(),
                SPAN(T('RATE'),': ', B(avg_rate or '---')),'[USD]. ',
                T('Network fee'), #.decode('utf8')
                ' - ', rr.xcurrs.txfee or 0.0001,'[',rr.currs.abbrev,'].',
                _class='col-sm-11'),
        _style='padding:5px', _class="row" + (odd and ' odd' or ''))
        odd = not odd
    h += H2(T('Fiat currencies'))
    odd = None
    curr_in, x, e = get_currs_by_abbrev(db, 'BTC')
    for rr in db((db.currs.used==True)
            & (db.currs.id==db.ecurrs.curr_id)).select(orderby=db.currs.name):
        b_rate, s_rate, avg_rate = get_average_rate_bsa(db, curr_in.id, rr.currs.id)
        #img_url = URL('shop','default','download', args=[rr.currs.icon])
        filename = os.path.join(path, rr.currs.abbrev + '.png')
        img_url = None
        if os.path.isfile(filename):
            img_url = URL('static','images/currs', args=[rr.currs.abbrev + '.png'])
        h += DIV(
            DIV(
                IMG(_src=img_url, _width=40, _height=40, _class="lst_icon") if img_url else '',
                _class='col-sm-1',
            ),
            DIV(
                B(rr.currs.name), ' [', rr.currs.abbrev, '] ',
                SPAN(' ', B('Not used'), '. ') if not rr.currs.used else '',
                SPAN(T('RATE'),': ', B(avg_rate or '---')),'[1/BTC]. ',
                #P(rr.currs.desr,'. ', _class='small'),
                _class='col-sm-11'),
        _style='padding:5px', _class="row" + (odd and ' odd' or ''))
        odd = not odd
    f = FORM(
        DIV(
            DIV(
                LABEL(T('Name'),': ',), INPUT(_name='curr'),BR(),
                LABEL('[',T('Abbreviation'),']: '), INPUT(_name='abbr'),
                _class='col-sm-8'),
            DIV(
                BUTTON('ADD', _type='submit', _class='btn btn-one btn-lg'),
                _class='col-sm-8'),
            _class='row'),
        )

    #print request.vars
    if f.accepts(request,session):
        response.flash = 'Not added, please email us for this currency'
    elif f.errors:
        response.flash = 'form has errors'

    ##print 'ff', response.flash
    h += DIV(
        H2(T('Add a fiat currency')),
        f,
        SPAN(response.flash, _style='color:red;') or '',
        _class='row')
    #return dict(h = h)
    return response.render(dict(h=DIV(h, _class='container')))

##@cache.action(time_expire=cache_expire, cache_model=cache.ram, quick='P')
def withdraw():
    return response.render()

##@cache.action(time_expire=cache_expire, cache_model=cache.ram, quick='P')
def index():
    return response.render()

@cache.action(time_expire=cache_expire, cache_model=cache.ram, quick='P')
def shop_add():
    res=DIV(T('Please use "Quick Registration" from payment module of Your shop. '),BR(),
            BR(),
            A(H4(T('See here')), _href=URL('default','join')),BR(),
            _class='container')
    response.not_show_function = True
    return response.render(locals())

@cache.action(time_expire=cache_expire, cache_model=cache.ram, quick='P')
def join():
    res = DIV(
            DIV(DIV(
                H4(T('For join')),
                UL(
                    T('Download free shop script from offical site (see URLs below) and install it.'),
                    T('Load extension for selected shop script and install it.'),
                    T('Set "shop ID" as Your wallet address in admin panel of payment extention.'),
                    T('Save settings and see success or error message.'),
                    T('Try make order and pay it.'),
                    ),
                _class='row', _style='margin: 60px 10px 20px 0px;'),
                _class='col-lg-5 col-sm-6 '),
            #DIV('',
            #    _class='col-lg-1'),
            DIV(no_img and '<img>' or IMG(_src=
                    #URL('static','images/prv/human-img-07.png')),
                    URL('static','images/prv/Career-Goal-Personal-Leadership.jpg')),
                _class='col', _style='margin-top: -50px;'),
            _class='row')
    odd = True
    st = 'padding:5px'
    col1 = 'col-lg-3 col-sm-4'
    col2 = 'col-md-4 col-sm-5'
    tab = DIV(
            DIV(XML('<i class="fa fa-home" style="color: yellow;"></i> '), T('Name & vers'), _class=col1),
            DIV(XML('<i class="fa fa-anchor" style="color: yellow;"></i> '), T('Download Links'), _class=col2),
            DIV(XML('<i class="fa fa-info" style="color: yellow;"></i> '), T('Info'), _class='col'),
            _class='row bg-2', _style=st)
    for r in db_ltc(db_ltc.modules.is_enabled==True).select(orderby=db_ltc.modules.script|db_ltc.modules.ver):
        odd = not odd
        tab +=DIV(
            DIV(r.script, ' ', r.ver, _class=col1),
            DIV(A(B(T('SHOP')), _href=r.url_shop, _target='_blank', _class='url'),' ',T('and'),' ',
                A(B(T('Extention')), _href=r.url_module, _target='_blank', _class='url'),
                _class=col2),
            DIV(XML(r.txt), _class='col small'),
            _class='row ' + (odd and 'odd' or ''), _style=st)
    res += BR()
    res += DIV(tab, _class='row col-lg-offset-2 col-md-offset-1', _style='font-size:24px;')

    '''
    res += STYLE(' \
   ul.hr { \
    margin: 0; /* Обнуляем значение отступов */ \
    padding: 4px; /* Значение полей */ \
   } \
   ul.hr li { \
    display: inline; /* Отображать как строчный элемент */ \
    margin-right: 5px; \
    padding: 3px; \
   } \
   ')
   '''
    res += DIV(
        H3(T('API'), ':'),
        P(A(B(T('Short API documentation')), _href=URL('api','index'),
          _class="btn btn-one btn-lg", _style="background-color:slategrey;")),
        H3(T('Developers libs'), ':'),
        P(
            A(B('PHP lib'), _href=URL('static','modules/LITEcash_lib_php.zip'),
              _class="btn btn-one btn-lg", _style="background-color:slategrey;")),
        )
    res += DIV(
        )

    return response.render(locals())


@cache.action(time_expire=cache_expire, cache_model=cache.ram, quick='P')
def more():
    return dict(h = T('Coming soon...'))

@cache.action(time_expire=cache_expire, cache_model=cache.ram, quick='P')
def tos():
    return response.render()

@cache.action(time_expire=cache_expire, cache_model=cache.ram, quick='P')
def priv_policy():
    return response.render()

@cache.action(time_expire=cache_expire, cache_model=cache.ram, quick='P')
def license():
    import os
    filename = os.path.join(request.env.gluon_parent, 'LICENSE')
    return response.render(dict(license=MARKMIN(read_file(filename))))

@cache.action(time_expire=cache_expire, cache_model=cache.ram, quick='P')
def support():
    response.view = 'generic-col-9.html'
    r = CAT(
        'email: ', B('adm@lite.cash'),', ',
        T('topics for discussion'), ': ', A(B(T('BitcoinTalk')), _href="https://bitcointalk.org/index.php?topic=935948.0", _target="_blank"), BR(),
        IFRAME(
        _id="forum_embed", _src="javascript:void(0)", _scrolling="no",
        _frameborder=0, _width=900,  _height=700),
        SCRIPT(
          "document.getElementById('forum_embed').src = \
     'https://groups.google.com/forum/embed/?place=forum/lite-cash' \
     + '&showsearch=true&showpopout=true&showtabs=false' \
     + '&parenturl=' + encodeURIComponent(window.location.href);",
            _type="text/javascript",
            )
    )

    return  response.render(locals())
