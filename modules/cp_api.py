#!/usr/bin/env python
# coding: utf8

EXPIRE_MAX = 60*24*100
EXPIRE_MINITS = 180

import base64, os
import datetime, time
from decimal import Decimal # тут преимущественно все в Decimal

#from gluon import *

from common import rnd_8
import db_common
import crypto_client
import orders_lib
import shops_lib

def log(db, l2, mess='>'):
    m = 'cp_api'
    print m, mess
    db.logs.insert(label123456789=m, label1234567890=l2, mess='%s' % mess)
def log_commit(db, l2, mess='>'):
    log(db, l2, mess)
    db.commit()

# из входных данных по номеру счета взять счет
def check_ars(db, request):
    # значит тут только номер заказа в нашем сервисе - без доп параметров
    # этого достаточно
    id = request.args(0)
    if not id: return { 'error': 'args is empty'}, None

    # выделим секрет
    ids = str(id).split('.')
    #print ids, ids[0].isdigit()
    if not ids[0].isdigit(): return { 'error': 'bill_id not a digits'}, None

    #isinstance( shop_order_id, int ):
    # возьмем только целую часть
    #id = int(ids[0])
    shop_order = db.shop_orders[ids[0]]
    if not shop_order: return { 'error': 'bill [%s] not found' % ids[0]}, None
    if shop_order.secr:
        # счет секретный - выдавать его только по секретному коду (хэш),
        # который в дробной части добавлен
        # возьмем дробную часть
        secr1 = len(ids) > 1 and ids[1]
        if secr1 != shop_order.secr:
            # добавим задержку на неудачный запрос
            time.sleep(10)
            return { 'error': 'bill [%s] is secret' % ids[0]}, None
    else:
        # был доступ без секретного ключа
        # - введем задержку на перебор
        # чтобы народ быстро не перебирал счета по АПИ
        time.sleep(1)

    return None, shop_order

def get_expire_on(dt, expire=EXPIRE_MINITS):
    return dt + datetime.timedelta(0, 60 * (expire or EXPIRE_MINITS) )

#######################################################################
# возвращает статус заказов с цено и сумму оплат длля безконечного заказа
def check(db, request):
    err, shop_order = check_ars(db, request)
    if err: return { 'error': err }

    status = request.vars.get('status', shop_order.status)
    s = 0
    if status.upper() in ['SOFT','FILL']:
        s = shop_order.payed_true + shop_order.payed_hard + shop_order.payed_soft
    elif status.upper() == 'HARD':
        s = shop_order.payed_true + shop_order.payed_hard
    else:
        s = shop_order.payed_true

    if shop_order.price and s > shop_order.price: s = shop_order.price

    curr = db.currs[shop_order.curr_id]
    res = { 'payed': rnd_8(s), 'curr': curr.abbrev, 'price': rnd_8(shop_order.price),
            'status': shop_order.status, 'order': shop_order.order_id }

    orders_lib.del_note(db, shop_order)

    return res

# pars:
# from (datetime)
# till (datetime)
# recs - int
# curr
# get_addrs - кто слал адреса выдаст
def info(db, request):
    err, shop_order = check_ars(db, request)
    if err: return { 'error': err }

    pars = request.vars
    pays = {}
    curr_filter = pars.get('curr')
    from_filter = pars.get('from')
    till_filter = pars.get('till')
    start_rec_filter = int(pars.get('start_rec') or 0)
    recs_filter = int(pars.get('recs') or 100)
    recs_last = int(pars.get('last') or 0)
    get_addrs = 'get_addrs' in pars # показывать ли адреса плательщиков в транзакциях
    all_fields = 'all_fields' in pars # показывать все поля счета

    next_rec = None
    i_s = start_rec_filter
    i_stp = start_rec_filter + recs_filter
    i = 0
    addresses = {}
    for order_addr in db(db.shop_order_addrs.shop_order_id == shop_order.id).select():
        xcurr = db.xcurrs[order_addr.xcurr_id]
        curr = db.currs[xcurr.curr_id]
        addresses[curr.abbrev] = order_addr.addr
        # проверим на фильтр по крипте входа
        if curr_filter and curr_filter != curr.abbrev: continue
        if get_addrs:
            conn = crypto_client.conn(curr, xcurr)
            #if not conn: continue
            #print conn
        xpays = []

        if recs_last: pay_ins = db(db.pay_ins.shop_order_addr_id == order_addr.id) \
                .select(orderby=~db.pay_ins.id, orderby_on_limitby=False, limitby=(0,recs_last))
        else: pay_ins = db(db.pay_ins.shop_order_addr_id == order_addr.id) \
                .select()
        for pay_in in pay_ins:
            i = i + 1
            # ограничим
            if i-1 < i_s: continue
            if i > i_stp:
                next_rec = i_stp # запомним что не все записи выбраны - тут нельзя вычитать иначе 0 может получиться и там он в IF не сработает
                break
            dt_st = '%s' % pay_in.status_dt
            if from_filter and from_filter > dt_st: continue
            if till_filter and till_filter < dt_st: continue
            payment_ = {
                          'amount': rnd_8(pay_in.amount),
                          'rate_order_id': pay_in.rate_order_id,
                          'amo_out': rnd_8(pay_in.amo_out),
                          'created_on': '%s' % pay_in.created_on, # DT не проходит в json
                          'status': pay_in.status, 'status_dt': dt_st,
                          'amo_ret': rnd_8(pay_in.amo_ret),
                          'txid': pay_in.txid,
                          'vout': pay_in.vout,
                          }
            returned_ = []
            for r_ret in db(db.pay_ins_returned.ref_id == pay_in.id).select():
                returned_.append({'txid':r_ret.txid, 'amo': r_ret.amount})
            if len(returned_)>0:
                payment_['returned'] = returned_
            if get_addrs:
                payment_['addrs'] = conn and crypto_client.sender_addrs(conn, pay_in.txid)
                #print payment_['addrs']


            xpays.append( payment_ )

        if len(xpays)>0: pays[curr.abbrev] = xpays
    curr = db.currs[shop_order.curr_id]
    #order_curr = db.currs[shop_order.order_curr_id]
    # тут отдельно считаюттся сумма по статусам if shop_order.price and s >  shop_order.price: s = shop_order.price
    res = { 'price': rnd_8(shop_order.price), 'curr': curr.abbrev,
           'addresses': addresses,
           'payments': pays, 'status': shop_order.status,
           'shop': shop_order.shop_id, 'order': shop_order.order_id,
           'SOFT': rnd_8(shop_order.payed_soft), 'HARD': rnd_8(shop_order.payed_hard), 'TRUE': rnd_8(shop_order.payed_true),
           'created_on': '%s' % shop_order.created_on,
           'TOTAL': rnd_8(shop_order.payed_soft + shop_order.payed_hard + shop_order.payed_true),
           }
    # в самом счете не хранится expire_on
    if shop_order.price: res['expire_on'] = '%s' % get_expire_on(shop_order.created_on, shop_order.expire)
    if all_fields:
        af = dict(shop_order)
        af.pop('delete_record')
        af.pop('update_record')
        #af.pop('shop_orders_notes')
        af['email'] = af['email'][:3] + '***' + af['email'][-3:]
        for (k,v) in af.iteritems():
            if "<class 'gluon.dal.LazySet'>" == '%s' % type(af[k]):
                af[k] = '...'
            elif v == 0:
                af[k] = 0
            else:
                af[k] = '%s' % v
        res['fields'] = af
    if shop_order.expire: res['expire'] = shop_order.expire
    if next_rec: res['next_rec'] = next_rec
    if shop_order.conv_curr_id:
        conv_curr = db.currs[shop_order.conv_curr_id]
        res['conv_curr'] = conv_curr.abbrev
    if 'get_payouts' in pars:
        payouts = {}
        if recs_last: draw_recs = db(db.bills_draws_trans.shop_order_id==shop_order.id) \
                .select(orderby=~db.bills_draws_trans.id, orderby_on_limitby=False, limitby=(0,recs_last))
        else: draw_recs = db(db.bills_draws_trans.shop_order_id==shop_order.id).select()
        for r in draw_recs:
            curr = db.currs[r.curr_id]
            if not curr.abbrev in payouts:
                payouts [  curr.abbrev ] = []
            payouts [  curr.abbrev ].append({r.txid: float(r.amo)})
        res['payouts'] = payouts

    orders_lib.del_note(db, shop_order)

    return res

#################################################
#################################################
# make order
# args[0] - shop_id
# vars - parameters
# http://127.0.0.1:8000/shop/api2/make/10?price=123.13
def make(db, request):

    shop_id = request.args(0)
    if not shop_id:
        return { 'error': 'request.args is empty'}, None

    # проверка на "просто" магазин - без регистраций
    # если да -то там будет вставлены параметры: public=1 conv_curr=ADDRESS_CURR
    shop, _ = shops_lib.is_simple_shop(db, request.vars, shop_id )
    if not shop:
        return { 'error': 'shop [%s] not found' % shop_id }, None

    price = request.vars.get('price', 0)
    if price and price < 0: price = 0

    abbrev = request.vars.get('curr', 'BTC') # по умолчанию BTC
    curr, _x, _e = db_common.get_currs_by_abbrev(db, abbrev)
    if not curr:
        # тут пока может быть любая валюта и фиат тоже
        # попробуем ее у Пай Пал стянуть
        import rates_yahoo
        err, pair_base = rates_yahoo.set_curr(db, abbrev)
        if err:
            # PayPal ну его нафиг
            #import rates_paypal
            #err, res = rates_paypal.set_curr(db, abbrev)
            #if err:
            log(db, 'make', { 'error': '[%s] not found as a currency' % abbrev, 'mess': '%s' % err })
            return { 'error': '[%s] not found as a currency' % abbrev }, None
        curr = db.currs[pair_base.curr1_id]

    # обязательные параметры все норм

    conv_curr = shop.simple_curr and db.currs[shop.simple_curr]
    conv_curr_abbr = request.vars.get('conv_curr')
    if not conv_curr and conv_curr_abbr:
        conv_curr,x,e = db_common.get_currs_by_abbrev(db, conv_curr_abbr)
        if not x:
             return { 'error': '[conv_curr=%s] not found as crypto-currency' % conv_curr_abbr }, None

    ###''' это тут нельзя делать а то за магазин счета будут создавать мошеники - и пользоваться как ширмой магазином
    # соберем параметр - выплата на адреса с весовыми коэффициентами а не в магазин
    addrs = {}
    addr_curr = None
    for (k,v) in request.vars.iteritems():
        if len(k)>30:
            try:
                v = float(v)
            except: # Exception as e:
                continue
            addrs[k]=v
            if not addr_curr:
                addr_curr, x, e = db_common.get_currs_by_addr(db, k)
                #print addr_curr
    if len(addrs) ==0: addrs=None
    # валюту конвертации поменяем если заданы авто-адреса выплат
    conv_curr = addr_curr or conv_curr
    ###'''

    # если надо что-то сохранить на сервисе и не переводить автоматом в магазин - то задаем:
    keep = request.vars.get('keep') or 0.0
    try:
        keep = float(keep)
    except: # Exception as e:
        keep = 0.0
    keep = keep > 1 and 1.0 or keep < 0 and 0.0 or keep

    # если задан Публичный параметр, то не делать секрет
    secr = None
    if 'public' not in request.vars:
        #secr = '%s %s %s' % (shop.id, order_id, datetime.now() )
        #secr = abs(hash( secr ))
        secr = base64.b64encode(os.urandom(6), '_-')[:8]

    # номер заказа может быть тоже пустой - тогда генерим свой случайный
    order_id = request.vars.get('order') or base64.b64encode(os.urandom(6), '_-')[:8]

    expire = None
    if price:
        expire = request.vars.get('expire')
        if expire:
            expire = int( expire )
            if expire < 10: expire = 20
            elif expire > EXPIRE_MAX: expire = EXPIRE_MAX

    shop_order_pars = dict(
            shop_id = shop.id,
            curr_id = curr.id,
            order_id = order_id,
            price = price,
            conv_curr_id = conv_curr and conv_curr.id or None,
            keep = keep,
            expire = expire,
            exchanging = request.vars.get('exchanging') and True or False,
            mess = request.vars.get('mess'),
            secr = secr, # секретный ключ если счет не публичный - чтобы другие его не могли смотреть в АПИ
            lang = request.vars.get('lang'),
            not_convert = 'not_convert' in request.vars, # если задан то не конвертировать
            curr_in = request.vars.get('curr_in'), # curr_in and json.dumps(curr_in) or None,
            curr_in_stop = request.vars.get('curr_in_stop'), #curr_in and json.dumps(curr_in) or None,
            back_url = request.vars.get('back_url'),
            note_on = request.vars.get('note_on') or shop.note_on,
            vol_default = request.vars.get('vol'),
            email = request.vars.get('email'), # можно сразу задать емайл для уведомлений
            # тут нельзя - только по команде от магазина! addrs = addrs,
            )
    #print shop_order_pars
    #log(db, 'make vars', request.vars)
    #log(db, 'make fields', shop_order_pars)
    shop_order_id = db.shop_orders.insert( **shop_order_pars )

    if price and Decimal(price) >0: # преобразуем в число
        # для ордеров с ценой - стек на просрочку добавим
        expire_on = get_expire_on(datetime.datetime.now(), expire)
        db.shop_orders_stack.insert( ref_id = shop_order_id, expire_on = expire_on )

    #####################################################
    # преобразуем в строчку иначе ошибка тут
    res = '%s' % shop_order_id
    if secr:
        res += '.%s' % secr
    return None, res

# проверяет учтена ли данная транзакция - если нет то запускает проверку на учет
# это может понадобиться если в кошельке появились АНСПЕНТ потраченые и они не зачлись
## check_txid/BTC/4c921268aa59a182f7268c211d9facdce5445d2306638b398cf1e7d8880a9266
def check_txid(db, request):
    curr = request.args(0)
    txid = request.args(1)
    if not txid or not curr:
        return {'error': 'check_txid/[CURR]/[txid]' }

    pay_in = db(db.pay_ins.txid==txid).select().first()
    if pay_in:
        so_addr = db.shop_order_addrs[pay_in.shop_order_addr_id]
        so = db.shop_orders[so_addr.shop_order_id]
        return { 'bill_id': so_addr.shop_order_id, 'status': pay_in.status }

    ## try check new txid
    time.sleep(1)
    import db_common
    curr, xcurr, ecurr = db_common.get_currs_by_abbrev(db, curr)
    if not xcurr:
        return {'error': '[CURR] not exist' }

    import crypto_client
    cn = crypto_client.conn(curr,xcurr)
    # если это транзакция не нашего кошелька то выдаст ошибку - облом для чужих
    tr = cn.gettransaction(txid)
    err = tr.get('error')
    if err:
        return err
    '''
amount	:
Decimal('0.04447648')
blockhash	:
00000000000000001744258240fa4d5dc213393cfc85e450537cd39e84865b4a
blockindex	:
0
blocktime	:
1422192344
confirmations	:
536
details	:
account	:
sh [BitRent.in] [25] [BTC]
address	:
1MfMcg8J7rKKGUNmGRvEhHCZHiqPzdAzoB
amount	:
Decimal('0.04447648')
category	:
generate
generated	:
True
hex	:
010000000100000
...
b861ad5d88ac00000000
time	:
1422192344
timereceived	:
1422192540
txid	:
3f2bf2fa360c0ceb8ff29309aad47c20cf9105769964f6c5d818d43a04062c10
walletconflicts	:
    '''
    ins = []
    vout = -1 # там сразу ++
    for r in tr['details']:
        vout += 1
        if r['category'] == 'send':
            continue

        addr = r['address']
        if not addr:
            # если адреса нет то берем его из рав-транзакции
            rawtr = cn.getrawtransaction(txid, 1)
            vouts = rawtr[u'vout']
            trans = vouts[vout]
            #print trans
            addr = trans[u'scriptPubKey'][u'addresses'][0]

        amo = r['amount']
        acc =  r['account'] or cn.getaccount(addr)
        ins.append({
            'acc': acc, 'amo': amo,
            'confs': tr[u'confirmations'],
            # запомним данные для поиска потом
            'txid':txid, 'vout': vout,
            'addr': addr,
            'time':tr[u'time']
            })

    if len(ins)==0:
        return { 'error': 'list of inputs is empty' }
    curr_block = cn.getblockcount()
    not_ret = False # пока без записи в БД
    from serv_block_proc import b_p_db_update
    need_commit =  b_p_db_update(db, cn, curr, xcurr, ins, curr_block, not_ret)
    if not_ret:
        ## не будем пока записывать
        db.rollback()

    return dict(need_commit=need_commit, ins=ins)
