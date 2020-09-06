# coding: utf8
from gluon.tools import Mail
#from decimal import Decimal

response.title=T("Подключение к международной платежной системе на основе криптовалют")
response.subtitle=' '
#response.big_logo2=True
#response.logo2 = IMG(_src=URL('static','images/7P-33.png'))

def note_test():
    #session.forget(response)
    response.title=T("Проба посылки уведомлений вашему магазину от нашего сервиса")
    f = FORM(
        LABEL(T('id магазина')),INPUT(_name='shop'),
        LABEL(T('id заказа')),INPUT(_name='order'),
        BR(),INPUT(_type='submit'),
        )
    if f.accepts(request.vars, session):
        import time
        time.sleep(3)
        shop = db.shops[f.vars.shop]
        if not shop:
            url_resp = T('ERROR: Shop not found')
        elif not shop.url:
            url_resp = T('shop url is empty')
        else:
            url_resp = shop.url + '/' + shop.note_url
            import urllib
            url_resp = url_resp + urllib.urlencode({'bill':1, 'order': f.vars.order})
        
    return locals()
    
def accept():
    import common
    if common.not_is_local(): raise HTTP(200, T('ERROR'))
    id = request.args(0)
    shop_add = id and db.shops_add[ id ]
    res = CAT()
    if not shop_add:
        res = SQLFORM.smartgrid( db.shops_add )
        return dict(res=res)
    
    res = SQLFORM(db.shops_add, shop_add)
    if res.accepts(request.vars, session):
        #response.flash = T('new record inserted')
        # берем ИД новой записи
        new_shop_id = res.vars.id
        shop = db(db.shops.name == res.vars.name).select().first()
        shop = shop or db(db.shops.url == res.vars.url).select().first()
        shop = shop or db(db.shops.email == res.vars.email).select().first()
        if shop:
            raise HTTP(500, T('Запись с такими данными уже есть, обратитесь к администратору для решения вопроса.'))

        pars = res.vars.copy()
        id_old = pars['id']
        # удалим лишние поля!
        for k in ['id', 'CMS']:
            _ = pars.pop(k)
            
        addr1 = pars.pop('wallet_BTC')
        addr2 = pars.pop('wallet_LTC')
        print pars
        new_shop_id = db.shops.insert( **pars )
        # теперь добавим кошельки
        import db_common
        if addr1:
            _, xcurr, _ = db_common.get_currs_by_addr(db, addr1)
            db.shops_xwallets.insert( shop_id = new_shop_id, xcurr_id = xcurr.id, addr = addr1 )
        if addr2:
            _, xcurr, _ = db_common.get_currs_by_addr(db, addr2)
            db.shops_xwallets.insert( shop_id = new_shop_id, xcurr_id = xcurr.id, addr = addr2 )
        del db.shops_add[ id_old ]
        print 'accepted'
        response.flash = ' ACCEPTED!'
        # надо сбросить параметр - редиректом
        redirect(URL('accept'))
    
    return dict(res=res)

def send_email_to_shop(shop):
    to_addr = shop.email
    if not to_addr or len(to_addr) < 6: return
    mail = Mail()
    mail.settings.server = 'smtp.yandex.ru' #:25'
    mail.settings.sender = 'support@cryptopay.in'
    mail.settings.login =  'support@cryptopay.in:huliuli'
    context = dict( rec = shop)
    mess = response.render('add_shop_mail.html', context)
    #print mess
    #to_addr = 'kentrt@yandex.ru' # 'icreator@mail.ru'
    mail.send(to=[to_addr],
           subject=T(T('Подключение к cryptoPay.in')),
           message=mess)

import db_common
import db_client

def download():
    return response.download(request, db)

def test_pay():
    print request.args
    print request.vars
    if not request.args or len(request.args)==0:
        raise HTTP(500, 'shop id not found')
    shop = db.shops_add[request.args[0]]
    if not shop:
        raise HTTP(500, 'new shop %s not found' % request.args[0])
    
    bill_id = 13
    uri = 'http://%s/%s%s' % (shop.url, shop.note_url, bill_id )
    form = FORM(T('Эмуляция оплаты клиента'),
        LABEL(T('')), INPUT(_type='submit', _value=T('Послать уведомление об оплате')),
        _action=uri, _method='post',
        )
    
    return dict(form=form, uri=uri, shop_id=shop.id, bill_id=bill_id)

def test_order_show():
    response.title=T("Оплата криптовалютами заказов из магазинов")

    if not request.args or len(request.args)==0:
        response.subtitle=T("Магазин не определен!")
        return dict()

    shop = db.shops_add[request.args[0]]
    if not shop:
        response.subtitle=T("Shop №%s not found!") % request.args[0]
        return dict()

    curr_abbr = request.vars.get('curr', 'BTC')
    curr_out, xcurr_out, ecurr_out = db_common.get_currs_by_abbrev(db, curr_abbr)

    if not curr_out:
        response.subtitle=T("Валюта [%s] не известна!") % curr_abbr
        return dict()

    img = None
    if shop.icon: img = IMG(_src=URL('default','download', args=['db', shop.icon]))
    #elif shop.img: img = XML('<img src="%s">' % shop.img)

    shops_url = shop.url or 'http://%s' % shop.name2
    response.vars = {}
    response.title=XML(XML(T("Параметры платежа для ") + '<BR>') + XML( img or '' ) + ' ' +\
            XML( A(shop.name, _href=shops_url, _target="_blank")))
    response.vars['s_url'] = XML( A(T('тут'), _href=shops_url, _target="_blank"))

    vars_emp=None
    if not request.vars or len(request.vars)==0:
        response.subtitle=T("Пустые параметры!")
        vars_emp = {'order':'?', 'user':'?'}
        #return dict()

    response.vars['curr_out'] = curr_abbr
    response.vars['shop_id'] = shop.id
    
    price = request.vars.get('price')
    response.vars['vol_readonly'] = price and True
    response.vars['price'] = price


    #payed = 0.0
    payed = request.vars.get('payed')
    if price:
        if payed:
            volume_out = float(price) - float(payed)
        else:
            volume_out = float(price)
    else:
        volume_out = 0.0
    volume_out = round(volume_out, 10)
    response.vars['volume_out'] = volume_out

    #print request.vars
    acc_pars = []
    vn = 'user'
    if vn in request.vars and len(request.vars[vn])>0 or vars_emp and vn in vars_emp:
        acc_pars.append({
                    'l': T('Идентификатор пользователя'),
                    'i': INPUT(_name= vn,
                         _value=request.vars[vn],
                         _readonly = not vars_emp,
                         _size=6,
                         #requires=IS_NOT_EMPTY(),
                         ),
                    })
    vn = 'order'
    if vn in request.vars and len(request.vars[vn])>0 or vars_emp and vn in vars_emp:
        acc_pars.append({
                    'l': T('Идентификатор заказа'),
                    'i': INPUT(_name= vn,
                         _value=request.vars[vn],
                         _readonly = not vars_emp,
                         _size=6,
                         #requires=IS_NOT_EMPTY(),
                         ),
                    })
    if 'mess' in request.vars: response.vars['shop_mess'] = request.vars['mess']

    curr_in_abbr = 'curr_in' in request.vars and request.vars['curr_in'] or None
    curr_in, xcurr_in, ecurr_in = db_common.get_currs_by_abbrev(db, curr_in_abbr)

    pairs = db_client.get_xcurrs_for_shop(db, volume_out, curr_out, shop) #, None, [curr_abbr])

    return dict(pars=acc_pars, xcurrs_list=pairs)

    
def test():
    if not request.args or len(request.args)==0:
        new_shop_id = session.shop_add_id
        if not new_shop_id:
            redirect(URL(index))
    else:
        new_shop_id = request.args[0]
    
    new_shop = db.shops_add[new_shop_id]
    #print new_shop_id, new_shop
    if not new_shop:
        redirect(URL(index))

    test_new_order = FORM(T('Тестровать создание заказа от вашего магазина'),
        LABEL(T('Заказ:')), INPUT(_name='order', _value='QWXE'),
        LABEL(T('Валюта:')), INPUT(_name='curr', _value='BTC'),
        LABEL(T('Цена заказа:')), INPUT(_name='price', _value='0.0077'),
        LABEL(T('Оплачено клиентом:')), INPUT(_name='payed', _value='0.0025'),
        LABEL(T('Сообщение клиенту:')), INPUT(_name='mess', _value='Hi!'),
        LABEL(T('')), INPUT(_type='submit', _value=T('Проверить')),
        _action=URL('test_order_show', args=[new_shop_id]), _method='post',
        )
    
    return dict(r = new_shop, test_new_order=test_new_order)

def index():
    
    redirect('http://LITE.cash/join')
    return dict(form = None, ll= None)

    #db.shops_add.truncate()
    shop_add_id = session.shop_add_id
    shop_add = shop_add_id and db.shops_add[shop_add_id] or None

    form = SQLFORM(db.shops_add, shop_add, # fields = ['name', 'name2', 'url', 'icon'],
        submit_button = T('Дальше >'),
        labels = {'name': XML(T('Имя магазина [name]')),
             'url': XML(T('Ссылка на магазин [url]<br>Включая http:// или https://')),
             'cat_id': T('Категория'),
             'note_url': XML(T('Ссылка<br>для уведомления [note_url]')),
             'note_on': XML(T('Статус<br>для уведомления [note_on]')),
             'back_url': XML(T('Ссылка для<br>возврата в магазин [back_url]')),
             'show_text': XML(T('Текст для<br>пользователя [shop_mess]')),
             'wallet_BTC': XML(T('Адрес кошелька<br>криптовалюты BTC')),
             'wallet_LTC': XML(T('Адрес кошелька<br>криптовалюты LTC')),
             'icon':T('Иконка [icon]'),
             },
        col3 = {
             'name': T('например "Новый"'),
             'url': T('например "http://novyi.com"'),
             'note_url': XML(T('Например "cp_response/"<br>тогда полная ссылка будет:<br>"novyi.com/cp_response/[order_id]"<br>Или "note_cpay?order_id="<br>тогда полная ссылка будет:<br>"novyi.com/note_cpay?order_id=[order_id]"')),
             'email': T('например "admin@novyi.com"'),
             'icon': T('.jpg .gif'),
             'show_text': T('Этот текст будет высвечиваться каждый раз когда будет создаваться ордер от Вашего магазина.'),
             'wallet_BTC': T('BTC. Скопируйте его сюда'),
             'wallet_LTC': T('LTC. Скопируйте его сюда'),
             },
        upload=URL('download'),
        )

    #form.vars['wallet'] = 'ddd'
    #print form.vars

    if form.accepts(request.vars, session):
        #response.flash = T('new record inserted')
        # берем ИД новой записи
        new_shop_id = form.vars.id
        shop = db(db.shops.name == form.vars.name).select().first()
        shop = shop or db(db.shops.url == form.vars.url).select().first()
        shop = shop or db(db.shops.email == form.vars.email).select().first()
        if shop:
            raise HTTP(500, T('Запись с такими данными уже есть, обратитесь к администратору для решения вопроса.'))

        session.shop_add_id = form.vars['id']
        redirect(URL('add', 'test', args=['%s' % form.vars['id']]))
        #return
    ll = SQLFORM.grid(db.shops_add,
        #label = T('Список участников'),
        #fields=f,
        deletable=False,
        editable=False,
        details=False,
        selectable=None,
        create=False,
        csv=False,
        )
    
    return dict(form = form, ll= ll)

def start():
    response.title=False
    #response.subtitle=T('Краткий путь в мир криптовалют')
    mm = CAT(
        H3(T('Начать принимать оплату в биткоинах на своем сайте со всего мира можно так:')),
        OL(
            LI(T('Настроить свой сайт на работу с нашим сервисом:'),
                OL(
                    LI(T('Если Вы обычный пользователь, то необходимо установить подходящиий'), ' ',
                    A(T('платежный модуль'), _href=URL('default','plugins')),', ',
                    T('или заказать разработку модуля у нас.')),
                    LI(T('Если Вы разработчик, то можете настроить работу с сервисом сами через'),' ',
                    A(B('API'), _href=URL('default','api_docs')),'. '),
                _type='a',
                )),
            CAT(T('Далее использовать один из способов взимодействия с нашим сервисом:'),
                OL(
                    LI(T('"Без регистрации" (быстро и просто) - по адресу кошелька'),'. ',
                        T('Если Вы используете готовый модуль, то при его настройке вместо ID магазина укажите адрес своего кошелька для выплат и, при сохранении настроек модуль совершит автоматическую регистрацию Вашего магазина (включая ссылки на лого, уведомления и возврат на сайт магазина).'),' ',
                        T('Если Вы не используете готовый модуль, автоматическая регистрация происходит при создании первого счёта для данного адреса кошелька. Будьте внимательны при такой регистрации, так как изменить данные будет невозможно - проверьте сначала правильность ссылок на лого магазина, ссылку для уведомлений и ссылку для возврата на сайт магазина'),'. ',
                        T('Вручную можно создать'), ' ',A(B('счёт на оплату'), _href=URL('bill','simple')), '. ',
                        T('В этом случае Вы будете получать выплаты себе на адрес кошелька почти без промедлений за вычетом небольшой комиссии.'),' ',
                        T('При этом не обязательно заключать каких-либо договоров с нашей службой.')),
                    LI(
                       A(T('"C регистрацией"'), _href=URL('add', 'index',)),' ',
                       T('(дешево и просто)'),'. ',
                        T('Зарегистрировав Ваш сайт на нашем сервисе и получив номер участника [shop_id] - задать его в настройках модуля как "номер магазина"'),
                        UL(
                            T('Для приема выплат только в криптовалюте, без конвертации ее в рубли или доллары (фиатные деньги) Вам так же не обязательно заключать с нами каких-либо договоров'),
                            T('Для конвертации платежей клиентов в фиатные деньги (рубли и доллары) Вам необходимо заключить договор с нами.')),
                    ),
                    _type='a',
                ),
                T('Во всех случаях выплаты с балансов магазинов производят не реже чем раз в сутки.'),
                ),
            LI(T('Проверить получение'), ' ' , A(B('уведомлений'), _href=URL('add','note_test')),
               '. '),
            LI(T('Создать вручную'), ' ', A(B('счёт на оплату'), _href=URL('bill','simple')), ' ',
               T('Для Вашего магазина'), '. '),
            _start="1", # _type="a"
            ),
        T(''),
        BR(),
        H3(T('Для разработчиков')),
        T('Кратко взаимодействие выглядит так:'), BR(),
        OL(
            LI(T('Создавать счет на оплату')),
            LI(T('Получать данные об оплате по заданному счету')),
            _start="1", _type="a"
            ),
        BR(),
        DIV(T('Проверка оплаты счета происходит так:'),
            OL(
                LI(T('Сервис шлет уведомление по указанному адресу после того как клиент оплатил счет через наш сервис')),
                LI(T('Ваш сайт запрашивает информацию об оплате у нашего сервиса')),
                _start="1", _type="a"
                )
            ),
        T('Более подробно смотрите в'), ' ', A(B('API'), _href=URL('default','api_docs')),
        )
    return locals()
