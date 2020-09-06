# coding: utf8
import common
# запустим сразу защиту от внешних вызов
if common.not_is_local(): raise HTTP(200, T('ERROR'))

from decimal import Decimal
import datetime
#import json

import rates_lib

def log(mess):
    print mess
    db.logs.insert(mess='CNT: %s' % mess)
def log_commit(mess):
    log(mess)
    db.commit()

#
# найти лучшую цену для пары и объема
# get_best_price_for_volume/NVC/RUB/10
def get_best_price_for_volume():
    if len(request.args) == 0:
        mess = 'len(request.args)==0'
        print mess
        return mess
    import db_client
    import db_common
    x, e, a_in = db_common.get_curr_by_abbrev(db,request.args[0])
    x, e, a_out = db_common.get_curr_by_abbrev(db,request.args[1])
    expired = datetime.datetime.now() - datetime.timedelta(5,600)
    s_b = len(request.args)<4 or request.args[3]=='sell'
    #s_b = not 3 in request.args or request.args[3]=='sell'
    print s_b
    print db_client.get_best_price_for_volume(db, a_in.id, a_out.id,
            float(request.args[2]), expired, s_b)

def get_average_rate_bsa():
    if not request.args: return 'get_average_rate_bsa/CURR/CURR'
    
    curr1 = db(db.currs.abbrev == request.args(0) ).select().first()
    curr2 = db(db.currs.abbrev == request.args(1) ).select().first()
    if not curr1 or not curr2: return 'cuurs not found'
    s, b, a = rates_lib.get_average_rate_bsa(db, curr1.id, curr2.id, '0')
    return dict(s=s, b=b, a=a)

#
# найти лучшую цену для пары и объема
# get_best_price_for_volume/NVC/RUB/10
def get_best_price_for_volume():
    if len(request.args) == 0:
        mess = 'len(request.args)==0'
        print mess
        return mess
    import db_client
    import db_common
    x, e, a_in = db_common.get_curr_by_abbrev(db,request.args[0])
    x, e, a_out = db_common.get_curr_by_abbrev(db,request.args[1])
    expired = datetime.datetime.now() - datetime.timedelta(5,600)
    s_b = len(request.args)<4 or request.args[3]=='sell'
    #s_b = not 3 in request.args or request.args[3]=='sell'
    print s_b
    print db_client.get_best_price_for_volume(db, a_in.id, a_out.id,
            float(request.args[2]), expired, s_b)


# выдает список для вычисления курса по степени объема
def get_rate_powers():
    if len(request.args) == 0:
        mess = 'len(request.args)==0'
        print mess
        return mess
    import rates_lib
    print 'TOOLS'
    curr_in = db(db.currs.abbrev==request.args[0]).select().first()
    best_rates = rates_lib.get_best_rates(db, curr_in, None, '0') # без протухания курсов
    res = ''
    for v in best_rates:
        res = res + '[%s]->[%s]=' % (curr_in.abbrev,db.currs[v].abbrev) + '%s' % best_rates[v]  + '<br>'
    return res

# get_rate/BTC/RUB
def get_rate():
    if len(request.args) <2:
        mess = 'len(request.args)==0 - [pay_in]/[pay_out]/[amo]'
        print mess
        return mess
    import rates_lib
    import db_common
    curr_in, x, e = db_common.get_currs_by_abbrev(db,request.args[0])
    curr_out, x, e = db_common.get_currs_by_abbrev(db,request.args[1])
    amo = float( len(request.args)>2 and request.args[2] or 1 ) / 10
    res = ''
    for i in range(1,6):
        amo = amo*10
        amo_out, rate_order, rate = rates_lib.get_rate(db, curr_in, curr_out, amo)
        res = res + '%s[%s] -> %s[%s] x%s /%s <br>' % (amo, curr_in.abbrev, amo_out, curr_out.abbrev, rate, rate and 1/rate or 0)
    return res

# for that pay_in
# tools/get_best_rate/1/20
def get_best_rate():
    if len(request.args) == 0:
        mess = 'len(request.args)==0 - [pay_in]/[amo]'
        print mess
        return mess
    import rates_lib
    pay_in = db.pay_ins[request.args[0]]
    shop_order_addr = db.shop_order_addrs[pay_in.shop_order_addr_id]
    shop_order = db.shop_orders[shop_order_addr.shop_order_id]
    xcurr_in = db.xcurrs[shop_order_addr.xcurr_id]
    curr_in = db.currs[xcurr_in.curr_id]
    curr_out = db.currs[shop_order.curr_id]
    amo = float(request.args[1])
    amo_out, rate_order, rate = rates_lib.get_rate(db,
        curr_in, curr_out, amo, pay_in.created_on, shop_order_addr)
    return '%s[%s] -> %s[%s] x%s /%s' % (amo, curr_in.abbrev, amo_out, curr_out.abbrev, rate, 1/rate)

def conv_pow():
    if len(request.args) <2:
        mess = 'len(request.args)==0 - [curr_in]/[curr_out]/[amo]'
        print mess
        return mess
    import rates_lib
    import db_common
    curr_in, x, e = db_common.get_currs_by_abbrev(db,request.args[0])
    curr_out, x, e = db_common.get_currs_by_abbrev(db,request.args[1])
    amo = float( len(request.args)>2 and request.args[2] or 1 )
    conv_amo = rates_lib.conv_pow(db, curr_in, amo, curr_out)
    print conv_amo, amo/conv_amo
    return conv_amo


# PayPal test currency
def rates_paypal_get():
    if not request.args: return 'rates_yahoo_get/[CURR1]/[CURR2]/...'
    import rates_paypal
    err, currs = rates_paypal.get_currs(request.args)
    return err or currs
def rate_paypal_set():
    abbrev = request.args(0)
    if not abbrev: return 'request.args(0) -> test_curr/[CURR]'
    import rates_paypal
    err, res = rates_paypal.set_curr(db, abbrev)
    if err:
        return err
    elif type(res) == 'int':
        return dict(res='inserted', curr = db.currs[res])
    else:
        return dict(res='already exist', curr = res)

def rates_yahoo_get():
    if not request.args: return 'rates_yahoo_get/[CURR1]/[CURR2]/...'
    import rates_yahoo
    err, currs = rates_yahoo.get_currs(request.args)
    return err or currs

def rate_yahoo_set():
    if not request.args: return 'rate_yahoo_set/[CURR]'
    import rates_yahoo
    err, res = rates_yahoo.set_curr(db, request.args(0))
    if err:
        return err
    elif type(res) == 'int':
        return dict(res='inserted', curr = db.currs[res])
    else:
        return dict(res='already exist', curr = res)

    
########################
### bs3b bil/show - rates
def bs3b_bill_show():
    if not request.args: return 'bs3b_bill_show/AMO/invoice_CURR'
    from applications.bs3b.modules.rates_pow import get_bill_rates
    ##from rates_pow import get_bill_rates
    shop = None
    curr = db(db.currs.abbrev == request.args(1)).select().first()
    xpairs = get_bill_rates(db, float(request.args(0)), curr, shop)
    return xpairs

##########################
## in SHOP
##
def shop_bill_show():
    ## при показе счета
    xpairs = closed and {} or db_client.get_xcurrs_for_shop(db, 0, curr, shop, shop_order.curr_in_stop, shop_order.curr_in)

    ## при показе выбранной валюты
    best_rate = None
    pr_b, pr_s, pr_avg = rates_lib.get_average_rate_bsa(db, curr_in.id, curr.id, None)
    #print pr_b, pr_s, pr_avg
    if pr_avg:
        # примерное кол-во найдем
        vol_in = volume_out / pr_b
        #print vol_in, curr_in.abbrev, '-->', volume_out, curr.abbrev
        # точный курс возьмем
        amo_out, _, best_rate = rates_lib.get_rate(db, curr_in, curr, vol_in)
    #print best_rate, pair
    if not best_rate:
        response.title=T("ОШИБКА")
        return dict(uri='[' + curr_in.name + '] -> [' + curr.name + ']' + T(' - лучшая цена не доступна.'), addr=None, shop_id=shop.id)

    volume_in = volume_out/best_rate
    # теперь добавим погрешность курса
    volume_in = common.rnd_8(rates_lib.add_limit( volume_in, xcurr_in.txfee * 3))
    # пересчет курса с погрешностью к курсу
    best_rate = volume_out/volume_in
    response.vars['best_rate']=best_rate
    response.vars['best_rate_rev']=1.0/best_rate
    response.vars['volume_in'] = volume_in

#########################################
## in OREDRS_LIB
def shop_orders_inputs_update():
    if not request.args: return 'shop_orders_inputs_update/amo/XCURR/ECURR'
    ## входящая - это валюта платежа
    curr = db(db.currs.abbrev == request.args(1) ).select().first()
    if not curr: return 'curr ' + request.args(1) + ' not exist'
    rates = rates_lib.get_best_rates(db, curr) # загодя возьмем курсы обмена для этой крипты
    for (k, v) in rates.iteritems():
        v.append(db.currs[k].abbrev)
    res = { 'rates': rates }
    ## выходящая это валюта счета
    #### curr_out = db.currs[shop_order.curr_id]
    curr_out = db(db.currs.abbrev == request.args(2) ).select().first()
    if not curr_out: return 'curr ' + request.args(2) + ' not exist'
    shop_order_addr = created_on = None
    amount = request.args(0)
    amo_out, rate_order, rate_ = rates_lib.get_amo_out(db, rates, shop_order_addr, curr_out,
                               amount, created_on)
    res['amo_out'] = amo_out
    res['rate_order'] = rate_order
    res['rate_'] = rate_
    
    return res
