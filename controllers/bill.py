# coding: utf8
## - тут язык запоминается в сессии - хотя надо это в кукиях хранить

# сессию не писать - и не тормозить другие апросы АЯКС
# AJAX тоже пользуют сессию - надо ее запретить
# http://web2py.com/books/default/chapter/29/04/the-core#session
## тут сессия иногда используется №№№ session.forget(response)

UPD_TIMEOUT=2000000
UPD_TIMES=40
UPD_TIMES_NEW=4
UPD_TIMES_SOFT=9
UPD_TIMES_HARD=20

import logging
logger = logging.getLogger("web2py.app.bs3b")
logger.setLevel(logging.DEBUG)


def download():
    session.forget(response) # не захватывать сессию - не тормозит другие АЯКС запросы
    return response.download(request,db)

import os
def curr_icon(curr):
    f = 'images/currs/'+curr.abbrev+'.png'
    if os.path.isfile('applications/' + request.application + '/static/' + f):
        return URL('static', f)

def index():
    session.forget(response)
    #response.flash = request.vars.get('error')
    return 'ind kjh kjh kjex'

def get_lowest_status(st_old, status):
    ## сюда первый раз входит статус от счета - поэтому есть FILL
    if status == 'NEW' or st_old == 'TRUE': return status
    if status == 'SOFT' and st_old != 'NEW': return status
    return st_old
def mess_auto_upd(timeout):
    ##if session.lang and T.accepted_language != session.lang:
    ##    T.force(session.lang)
    return timeout and CAT(TAG.i(_class='fa fa-spin fa-refresh'), ' ',
                  T('Auto-updating each %s sec') % (timeout),
                  #' session.UPD_IS: ', session.UPD_IS
                  ) or ''

# создаем функию изменения перезагрузки в миллисекундах
def remake_reload_script(timeout=None):
    return SCRIPT('''
        var jelement = $("#show_update");
        var element = jelement.get(0);
        var statement = "jQuery('#show_update').get(0).reload();";
        clearInterval(element.timing); // остановим тот который был запущен
        ''' + \
        (timeout and '''
        element.timeout = %s000;
        element.timing = setInterval(statement, %s000); // запустим с новыми параметрами
        ''' % (timeout, timeout) or '')
        )

# при нажатии на кнопку для запука кошелька для платежей - сбросим скорость обновлений
def set_fast_reloads():
    session.UPD_IS = 0
    #return "$('#show_update').get(0).reload();" #перегрузим счетчик обновлений
    response.js = "$('#show_update').get(0).reload();"


## нажата кнопка - задания величины пополнения счета - просто обновим данные
def set_want_pay():
    session.want_pay = request.vars.get('want_pay')
    session.show_sel_curr = True
    if session.want_pay:
        session.want_pay = session.want_pay.replace(".", "", 1).isdigit() and float(session.want_pay) or 0.0
        ## это теперь не надо if session.UPD_TIMES and session.UPD_TIMES < 2:
        ##    redirect( request.env.http_web2py_component_location,client_side=True)

        #return "jQuery('#show_update').get(0).reload();"
        response.js = "$('#show_update').get(0).reload();"


def to_pay_btn(name, curr, val_to_pay, rate, to_pay=None):
    return CAT(
        DIV(
            DIV(IMG(_src=curr_icon(curr), _width=to_pay and 60 or 50, _alt=''),
                _class='col-sm-' + (to_pay and '4' or '3')),
            DIV(to_pay and CAT(BR(),B(T('Click to pay'))) or B(T('Click for get a %s address') % name),
                _class='col-sm-8 center-block white-space-normal'),
            _class='row'),
        H3(to_pay and '*' or '',val_to_pay,
          #_style='margin-top:0px;margin-bottom:3px;',
          ),
        rate, ' <> ', 1/rate,
        )
# создана кнопка с адресом для платежа
def to_pay_1(shop_order_id, curr, xcurr_in_id, val_to_pay, rate, shop_name, addr):
    btn_content = to_pay_btn(curr.name, curr, val_to_pay, rate, addr)
    from db_client import make_x_acc_label
    u_label = make_x_acc_label(None, shop_name or '', shop_order_id, '%sLITE.cash > %s > order_%s')
    from common import uri_make_url, rnd_8
    # сбросим сччетчик обновлений на быстрый и перегрузим главный элемент
    return DIV(
            A(
                #BUTTON(
                btn_content,
                   #_style='margin-top:-10px;margin-bottom:-10px;min-width: 250px',
                   #),
                _href=uri_make_url(curr.name2, addr, {'amount':rnd_8(val_to_pay), 'label': u_label} ),
                _onclick= "ajax('%s', [], '');" # eval not need':eval');"
                    % URL('bill','set_fast_reloads'),
                _style='display:block;padding:15px;',
                _class='btn_pay',
                ),
            TAG.font(T('Or send a coins to address'), ':', BR(), addr, _size=2),
        _style="margin:0;",
        _class='row')

def to_sel_1(shop_order_id, curr_in, xcurr_in_id, curr_id, val_to_pay, rate, shop_name):
    tag_to_pay = 'tp_%s' % xcurr_in_id
    return DIV(
        #TAG.font(TAG.i(_class='fa fa-spin fa-spinner'), _size=50, _style='dysplay:none;position:absolute;left:40px;top:20px;'),
            #BUTTON(
            A(to_pay_btn(curr_in.name, curr_in, val_to_pay, rate),
            _onclick= """
                ajax('%s', [], '%s');
                $('#%s').animate({ height: 'h_ide', opacity: 0.3 }, 'slow');
                $('#%s').prop('disabled', true);
                """ % (URL('bill','to_pay_make', args=[shop_order_id, xcurr_in_id, curr_id ],
                        vars={'v': val_to_pay, 'r': rate, 'n': shop_name }), tag_to_pay, tag_to_pay, tag_to_pay),
            #_style='margin:10px;min-width: 250px',
            _style='display:block;padding:15px;',
            _class='btn_sel',
            ),
        _style="margin:0;",
        _class='row')

# это вызов с параметрами без проверки
def to_pay_make():
    session.forget(response) # не захватывать сессию - не тормозит другие АЯКС запросы

    xcurr_id = request.args(1)
    tag_to_pay = 'tp_%s' % xcurr_id
    r = CAT(SCRIPT("$('#%s').animate({ height: 'sh-ow', opacity: 1 }, 'slow'); \
             $('#%s').prop('disabled', false);" % (tag_to_pay, tag_to_pay)))

    xcurr = db.xcurrs[xcurr_id]

    curr = xcurr and db.currs[ xcurr.curr_id ]
    if not curr: return r + T('pay currency not found')
    curr_out = db.currs[request.args(2)]
    if not curr_out: return r + T('out currency not found')
    val_to_pay = float(request.vars.get('v') or 0)
    rate = float(request.vars.get('r') or -1)

    shop_order_id = request.args(0)
    ##shop_order = db.shop_orders[shop_order_id]
    # найдем адресс кошелька для данной крипты и нашего заказа
    shop_name = request.vars.get('n') or '_'
    from db_client import make_x_acc, get_shop_order_addr_for_xcurr
    x_label = make_x_acc(None, shop_order_id, curr.abbrev, '%s%s%s')
    try:
        shop_order_addr = get_shop_order_addr_for_xcurr(db, shop_order_id, curr, xcurr, x_label)
    except:
        shop_order_addr = None
    if not shop_order_addr:
        return r + CAT(
                to_sel_1(shop_order_id, curr, xcurr.id, curr_out.id, val_to_pay, rate, shop_name),
                DIV(T('Connection to') + ' [' + curr.name + '] ' + T('is broken.' + ' ' + T('Please try late.')),
                    _class='bg-danger'),
            )
    ## Попытаемся сразу вызвать кошелек без повтороного нажатия на кнопку
    addr = shop_order_addr.addr
    from db_client import make_x_acc_label
    u_label = make_x_acc_label(None, shop_name or '', shop_order_id, '%sLITE.cash > %s > order_%s')
    from common import uri_make_url, rnd_8
    open_wallet="location.href='%s'" % uri_make_url(curr.name2, addr, {'amount':rnd_8(val_to_pay), 'label': u_label} )
    #response.js = "location.href='%s'" % 'bitcoin:1234?amo=123'
    response.js = open_wallet
    return to_pay_1(shop_order_id, curr, xcurr.id, val_to_pay, rate, shop_name, addr) + r

# обновление статуса, платежей и остатков
# тут делаем полную проверку на секретность по check_args
def show_update():
    ## тут она используется
    ## session.forget(response) # не захватывать сессию - не тормозит другие АЯКС запросы

    #scr_show =
    r = CAT(
            SCRIPT("""
                if ( ! $('#show_update').is(':visible')) {
                    $('#show_update').animate({ height: 'show' }, 1000);
                }
                $('#is_spin').html('');
                """)
        )

    from common import rnd_8
    from cp_api import check_ars
    err, shop_order = check_ars(db, request)
    if err:
        # ошибка или секрет сработал
        logger.warn( err )
        return r + DIV(BEAUTIFY(err), _class='bg-danger col-sm-12')

    # message on STATUS
    st = shop_order.status
    ret_now = False
    if False: pass
    elif st == 'NEW':
        mess = T('Invoice was created, awaiting a payments...')
    elif st == 'FILL':
        mess = T('The invoice is replenished...')
    else:
        ret_now = True
        cls = 'success'
        if st == 'SOFT':
            mess = T('The bill is paid in full, but at least one payment still has the status of a SOFT')
            timeout = 10
            cls = 'info'
        elif st == 'HARD':
            mess = T('The bill is paid in full, but at least one payment still has the status of a HARD') + '. ' \
                + T('To return to the store click on the order number')
            timeout = 30
        elif st == 'CLOSED':
            mess = T('The bill is paid in full.') + '. ' \
                + T('To return to the store click on the order number')
            timeout = None
        elif st == 'EXPIRED':
            mess = T('Invoice expired, all payments are returned') + '. ' \
                + T('To return to the store click on the order number')
            cls = 'danger'
            timeout = None
        else:
            mess = T('Invoice is invalid')
            timeout = None
            cls = 'danger'

    if ret_now:
        # выходим тут - статус уже большой
        return r \
                + DIV(mess_auto_upd(timeout), _class='row') \
                + DIV(H4(T('Status'), ': ', B(st)), '*',mess,
                      _style='padding:5px 15px;',
                      _class='row block-center bg-' + cls ) \
                + remake_reload_script(timeout)


    curr = db.currs[shop_order.curr_id]
    accuracy = curr.accuracy or 3

    h = CAT(SCRIPT(
           "if ( ! $('#inputs').is(':visible')) { \
                $('#inputs').animate({ height: 'show', opacity: 'show' }, 'slow'); \
            }",
            ),
            CAT(H3(T('Income payments in progress'), ' ',
                 TAG.i(_class='fa fa-spin fa-cog'))) or '',
        )
    # тут кукрс будет вычислен быстро по базе и степени
    # тут берем именно ВАЛЮТУ_ЗАКАЗА чтобды курс показывался и для валюты конвертации
    shop_order_id = shop_order.id
    shop = db.shops[shop_order.shop_id]

    payed = shop_order.payed_soft + shop_order.payed_hard + shop_order.payed_true
    price = shop_order.price
    to_pay = Decimal(0)
    if price:
        if price > payed:
            to_pay = price - payed
    else:
        ### _value= round(isinstance(session.want_pay, float)
        ###          and session.want_pay or shop_order.vol_default or 0.0, accuracy),
        to_pay = session.want_pay and Decimal( session.want_pay) or shop_order.vol_default or 0.1

    from rates_pow import get_bill_rates
    xpairs = get_bill_rates(db, float(to_pay), curr, shop, shop_order.curr_in_stop, shop_order.curr_in)
    #print xpairs

    r_ps_t = CAT()
    r_ps_t += THEAD(TR(TH(T('Status')),TH(T('Incomed Amount')), TH(T('Accepted Amount')), TH(T('Created On')), TH(T('vout:txid'))))
    ins = db((db.pay_ins_stack.ref_id == db.pay_ins.id)
             & (db.pay_ins.shop_order_addr_id == db.shop_order_addrs.id)
             & (db.shop_order_addrs.shop_order_id == shop_order.id)
             ).select()
    est_payed = Decimal(0)

    st_pay = 'CLOSE'
    if ins:
        for rec in ins:
            p = rec.pay_ins
            # возьмем самы низкий статус у платежей
            st_pay = get_lowest_status(st_pay, p.status)
            xc = db.xcurrs[rec.pay_ins_stack.xcurr_id]
            if not xc:
                logger.error( 'db.xcurrs[rec.pay_ins_stack.xcurr_id] = NONE \n%s' % rec, request )

            cc = db.currs[xc.curr_id]
            if p.amo_out:
                amo_out = p.amo_out
            else:
                # найдем примерную величину по текущему курсу обмена
                rate = xpairs[cc.id]
                amo_out = p.amount / Decimal(rate['rate'])
                est_payed += amo_out
                amo_out = 'est. %s' % round(amo_out, curr.accuracy)
            r_ps_t += TR(p.status, '%s %s' % (cc.abbrev,p.amount),
                         amo_out, p.created_on,
                         A(TAG.bigger(TAG.i(_class='fa fa-info-circle ')),
                            #_class='btn',
                            _href=URL('api','tx_info',args=[cc.abbrev,p.txid]),
                            _target='_blank'))
            pass
    r_ps = DIV(
                DIV(h,TABLE(r_ps_t,
                     #_caption=T('Income payments in progress'),
                     _class='table table-striped table-condensed table-hover'),
                    _class='col-sm-12'),
                _class='row'
                )
    r += r_ps # list of payment in process

    mess_est_payed = est_payed >0 and ' ' + T('(estimated)') or ''
    if price:
        if price > Decimal(0.98)*(payed + est_payed):
            r_st_pay = CAT(DIV(H2(TAG.font(TAG.i(_class='fa fa-warning'), _color='red'),' ',
                  T('Left to pay'), mess_est_payed, ' ', B(round(float(to_pay),accuracy)), ' ', curr.abbrev)))
        else:
            r_st_pay = CAT(DIV(H2(TAG.font(TAG.i(_class='fa fa-check-circle '), _color='green'),' ',
                  T('The bill is paid'), mess_est_payed)))
    else:
        r_st_pay = CAT(
                SCRIPT( # если есть кнопка want_pay_go то ее отсановим
                  "document.getElementById('want_pay_go').innerHTML = '<i class=\"fa fa-refresh\" />';"),
                DIV(H3(T('On pay'), ' ', B(round(float(to_pay),accuracy)), ' ', curr.abbrev),
                  _class=''),
                )

    if est_payed and price:
        to_pay -= est_payed
        change = price * Decimal(0.02)
        if to_pay < -change:
            # если переплата велика то вернем
            r_st_pay += DIV(T('Estimated change'), ': ', -round(float(to_pay+change), accuracy))
        elif to_pay:
            # если недоплата
            r_st_pay += DIV(T('Estimated left to pay'), ': ', round(float(to_pay), accuracy))
    # переопределим время обновления
    ## плавно будем менять время обновления с 3-х сек до 100 сек
    if session.UPD_IS == None: session.UPD_IS = 8
    upd_is = session.UPD_IS
    if st_pay == 'NEW' and upd_is > UPD_TIMES_NEW:  upd_is = UPD_TIMES_NEW
    elif st_pay == 'SOFT' and upd_is > UPD_TIMES_SOFT:  upd_is = UPD_TIMES_SOFT
    elif st_pay == 'HARD' and upd_is > UPD_TIMES_HARD:  upd_is = UPD_TIMES_HARD

    if upd_is <= UPD_TIMES_NEW:
        timeout = 5
    elif upd_is <= UPD_TIMES_SOFT:
        timeout = 10
    elif upd_is <= UPD_TIMES_HARD:
        timeout = 20
    elif upd_is <= UPD_TIMES:
        timeout = 60
    else:
        timeout = 300
    if upd_is < UPD_TIMES: session.UPD_IS = upd_is + 1

    r_st = DIV( mess_auto_upd(timeout), _class='col-sm-4')
    r_st += DIV(r_st_pay, _class='col-sm-4')
    r_st += DIV(
                DIV(H4(T('Status'), ': ', B(st),
                   not price and
                       CAT(BR(),T('Payed'), est_payed and CAT(' (', T('estimated'), ')') or '',
                           ': ', B(round(float(payed),accuracy)),
                           est_payed and CAT(' (',B(round(float(payed + est_payed), accuracy)), ')') or '')  or ''),
                   mess, _class='bg-info'),
              _class='col-sm-4')
    r += DIV(r_st, _class='row')

    if to_pay < 0: to_pay = 0
    if not to_pay > 0:
        if price:
            # все оплачено - не показывать кнопки выбора валют
            return r + remake_reload_script(timeout)

    #print to_pay
    '''
    if not price and shop_order.exchanging and curr:
        # для обменных операций - показать резервы и не более резерва дать оплатить
        reserve = db_common.get_reserve( curr )
        i = 0
        for xp in xpairs:
            if xp['abbrev'] == curr.abbrev:
                break
            i = i + 1
        xpairs.pop(i)
    '''
    ##xpairs = {}
    if len(xpairs)==0:
        return r + DIV(H3(T('Raitings for this currency not found')), _class='bg-danger') \
            + remake_reload_script(timeout)

    r_xp = CAT()
    for (curr_in_id, pair) in xpairs.iteritems():
        ##print pair
        rate = pair['rate'] or 0
        curr_in = pair['curr']
        #curr_in_id = curr_in.id
        xcurr_in = db(db.xcurrs.curr_id == curr_in_id).select().first()
        if not xcurr_in: continue # это не крипта
        xcurr_in_id = xcurr_in.id

        #print curr_in.name, rate
        if rate >0:
            rate_show = rate
            rate = rate * (1 + pair['add_change'] * 0.01) # добавим погрешность на курс для быстрого зачета монет
            val_to_pay = round( rate * float(to_pay), curr_in.accuracy)
            #print val_to_pay
            shop_order_addr = db((db.shop_order_addrs.shop_order_id==shop_order_id)
                & (db.shop_order_addrs.xcurr_id==xcurr_in_id)
                ).select().first()
            #print shop_order_addr
            from common import get_host
            url_s = get_host(shop.url or '_') # обрежеи ссылку до имени
            shop_name = not shop.simple_curr and shop.name or url_s
            if shop_order_addr:
                # кнопка уже для запуска кошелька по URI
                btn = to_pay_1(shop_order_id, curr_in, xcurr_in_id, val_to_pay, rate_show, shop_name, shop_order_addr.addr)
            else:
                # кнопка для создания адреса для данной крипты
                btn = to_sel_1(shop_order_id, curr_in, xcurr_in_id, curr.id, val_to_pay, rate, shop_name) # тут курс без наценки поокажем

            r_xp += DIV(btn,
                _style='padding:10px;',
                _id='tp_%s' % xcurr_in_id, # target for button TO_PAY + ADDRES
                _class='col-lg-4 col-sm-6')
            #print curr_in.name

    if len(r_xp)==0:
        return r + DIV(H3(T('Ratings for that currency not found, try late')), _class='bg-danger') \
                  + remake_reload_script(timeout)

    r += DIV(DIV(
             DIV(H3(T('Select currency for payment'), '. ',
                    TAG.small(T('You can pay the invoice in several payments in different currencies'))),
                     P(T('*Change will be returned to you')), _class='col-sm-12'),
                 DIV(r_xp, _class='row'),
                 SCRIPT("if ( ! $('#sel_curr').is(':visible')) $('#sel_curr') \
                        .animate({ height: 'show', opacity: 'show' }, 'fast');"
                    ),
                _id='sel_curr',
                _style= session.show_sel_curr and 'height:0%; display:none;' or '',
                _class='col-sm-12'), # выравнивает по полям записи - не обрезает при выпадении
            _class='row')
    session.show_sel_curr = False

    return r + remake_reload_script(timeout)

def show():

    from cp_api import check_ars
    err, shop_order = check_ars(db, request)
    if err:
        # ошибка или секрет сработал
        from time import sleep
        sleep(5)
        logger.warn( err, request )
        raise HTTP(500, BEAUTIFY(err))

    shop_order_id = shop_order.id

    r = CAT()
    
    # если задан язык представления то переведем
    lang = request.vars.get('lang', shop_order.lang)
    if lang:
        session.lang = lang
        if 'lang' in request.vars: request.vars.pop('lang') # уберем его из параметров вверху
    ##print session.lang, T.accepted_language, session.lang != T.accepted_language
    if session.lang and T.accepted_language != session.lang:
        T.force(session.lang)
    lang = lang or session.lang or T.accepted_language
    if not LANGS[lang]:
        ## ессли в ннашем списке нет принятого языка самим фраймворком, то выберем английский
        lang = 'en'

    shop = db.shops[shop_order.shop_id]
    curr = db.currs[shop_order.curr_id]

    from common import get_host
    url_s = get_host(shop.url or '_') # обрежеи ссылку до имени
    shop_name = not shop.simple_curr and shop.name or url_s

    shops_url = back_url =  shop.url or shop.name and 'http://%s' % shop.name or None
    if back_url:
        empty_url = '?'
        if shop.back_url:
            back_url += '/' + shop.back_url
            empty_url = ''
        if shop_order.back_url:
            back_url += '/' + shop_order.back_url
            empty_url = ''
        back_url += empty_url + ('%s' % shop_order.order_id)

    img = None
    _width = request.is_mobile and 150 or 250
    if shop.icon:
        img = IMG(_src=URL('download', args=['db', shop.icon]), _width=_width, _alt='')
    elif shop.icon_url and shop.url:
        img = IMG(_src=shop.url + '/' + shop.icon_url, _width=_width, _alt='')

    so_secr_id = '%s' % shop_order_id
    if shop_order.secr: so_secr_id += '.%s' % shop_order.secr

    shop_order_url = URL('bill','show', args=[so_secr_id])
    
    langs = []
    for (n,l) in LANGS.iteritems():
        if n == lang_curr: continue
        langs.append(
            A(IMG(_src=URL('static', 'images/flags/' + l[1]), _width=30, _alt=''), ' ',l[0],
                #_href=request.url + '?lang=' + n, # тут вставляет имя апликатион, а нам не надо bs3b там видеть
                _href=URL('bill','show', args=[so_secr_id], vars=dict(lang=n)),
                _class='dropdown')
            )
    langs_menu = UL(LI(
                XML('<a href="#" class="dropdown-toggle" data-toggle="dropdown" data-hover="dropdown" data-close-others="true">%s</a>' % CAT(IMG(_src=URL('static', 'images/flags/' + _lang[1]), _width=30, _alt=''), ' ', _lang[0])),
                UL(langs, _class='dropdown-menu dropdown-megamenu'),
                _class="dropdown"),
            _class="nav navbar-nav"
            )

    curr_icon_f = curr_icon(curr)
    
    accuracy = curr.accuracy or 3
    price = shop_order.price
    if price>0:
        price_row = CAT(T('Price'), ': ', round(price, accuracy),
                curr_icon_f and IMG(_src=curr_icon_f, _width=44, _class='lst_icon', _alt='') or '[%s]' % curr.abbrev)
    else:
        price_row = CAT(
            FORM( # заставит по Enter запускасть событие клика на BUTTON
                INPUT(_name='want_pay', _value= round(isinstance(session.want_pay, float)
                                                      and session.want_pay or shop_order.vol_default or 0.0, accuracy),
                   _id='ttt', _autofocus=1,
                   _style='padding-left:50px;width:9em;'),
                curr_icon_f and IMG(_src=curr_icon_f, _width=48, _class='want_pay_icon', _alt='',
                    _style='position: absolute;left: -3px;') or DIV('[%s]' % curr.abbrev, _class='want_pay_icon', _style='position: absolute;left: -3px;'),
                BUTTON(TAG.i(_class='fa fa-refresh'), _name='want_pay',
                   _type='submit',
                   _class='btn btn-primary', _id='want_pay_go',
                   # тут вызов обновления LOAD внутри - чтобы последовательно было
                   _onclick= """
                       ajax('%s', ['want_pay'], '');""" # eval not need':eval');"""
                                % URL('bill','set_want_pay') +
                       """$('#want_pay_go').html('<i class=\"fa fa-spin fa-refresh\" />');
                       $('#sel_curr').animate({ height: 'hide'  }, 'slow');
                       $('#ttt').focus();
                       """
                ),
              _action="javascript: void(0);" ## не перегружает страницу при нажатии на кнопку SUBMIT
              )
            )

    
    #XML('<font size=30px color=#209F99>LITE<orange><i class="fa fa-btc"></i></orange>Cash</font>')
    r_logo = DIV(A(SETS.text_logo, _class='bill_logo',
                   _href=URL('default','index'), _target='_blank'),BR(),
            langs_menu)
    r_nums = CAT(H3(
        DIV(
            DIV(
                DIV(TAG.i(_class='fa fa-spin fa-refresh orange-16'), _id='is_spin'),
                _class='col-sm-1'),
            DIV(
                DIV(
                    DIV(T('Invoice'), ': ', A(shop_order_id, _href=shop_order_url), _class='col-sm-7'),
                    DIV(A(TAG.i(_class='fa fa-info-circle '),' ',T('Info'),
                          _href=URL('api_bill','info', args=[so_secr_id]), _class='bt'),
                        _class='col-sm-4'),
                    _class='row'),
                DIV(
                    DIV(T('Order'), ': ', A('%s' % shop_order.order_id, _href=back_url), _class='col-sm-8'),
                    _class='row'),
                _class='col-sm-11'),
            _class='row'),
        DIV(price_row, _class='row', _id='want_pay1'),
        ))
    r_sh_logo = A(img or shop_name, _href=shops_url, _target="_blank")
    r += DIV(
            DIV( r_logo,  _class='col-md-3 col-sm-4' ),
            DIV( r_nums,  _class='col-md-offset-1 col-sm-5' ),
            DIV( r_sh_logo, _class='col-sm-2'),
        _class='row')
    text = shop.show_text
    mess = shop_order.mess
    if text or mess:
        row = CAT()
        if mess:
            row += DIV(H3(T('Order info'), ': ', mess),
                _class='col-lg-offset-1 col-lg-6 col-sm-7')
            row += DIV(
                _class='col-lg-1 col-sm-0')
        if text:
            row += DIV(text,
                _class='col-sm-offset-9')
        r += DIV( row,  _class='row')

    ##session.UPD_TIMES = UPD_TIMES
    session.UPD_IS = UPD_TIMES_SOFT + 1
    r += LOAD('bill', 'show_update', args=[so_secr_id], ajax=True,
                times = 'infinity', timeout=UPD_TIMEOUT,
                target='show_update', # вместо _id
                _style='display:none; height:0%;',
                _class='container', #  ### !!!! обязательно нужен - иначе анимация сбивается!
            )

    return dict(r=r)
