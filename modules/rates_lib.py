#!/usr/bin/env python
# coding: utf8

# TODO
## курс для 1р по созданному счету потом уменьшается оплата
# check_args - убрать


#from gluon import *
import datetime
# тут преимущественно все в float -- from decimal import Decimal

ORDER_TIME = 1800 # в сек жизни заказ на обмен
TRANS_TIME = 300 # в сек жизни заказ на обмен задержка создания транзакции
RATES_TIME = 600 # в сек жизни курса с биржи

import db_common

# :: /bill/pay
# :: orders_lib.update_payed -1, -1
# :: orders_lib.inputs_update -1, -1
# добавим погрешность к величине с доп коэфф на комиссию и таксу сети
# 0.5% комиссии и 2 таксы сети
def add_limit( vol, txfee, tax_k=1.0, fee_k=1.0):
    v = 1
    if tax_k:
        if tax_k > 0:
            v = 1.0 + 0.005 * tax_k
        else:
            v = 1/( 1.0 - 0.005 * tax_k) # тут минус на минус = + и делим на него
    
    return float(vol) * v + (txfee and float(txfee) * 2.0 * fee_k or 0.0)
        

# :: serv_blocks.run_blocks
# удалим из стека просроченные чтобы не мешались
def check_orders(db):
    dt_order = datetime.datetime.now() - datetime.timedelta(0, ORDER_TIME)
    for r in db(db.rate_orders_stack).select():
        if r.created_on < dt_order:
            # заказ на курс просрочен
            del db.rate_orders_stack[r.id]

# :: get_average_rate_bsa
def add_tax(db, in_id, out_id, b, s):
    ex_tax = db((db.exchg_taxs.curr1_id==in_id)
                & (db.exchg_taxs.curr2_id==out_id)).select().first()
    tax = (ex_tax and float(ex_tax.tax) or 0.5)*0.01
    if b: b = b * (1-tax)
    if s: s = s / (1-tax)
    return b, s

# rate for buy, sell, average or None
def get_average_rate_bsa_1(db, in_id, out_id, expired):

    pair = db((db.exchg_pair_bases.curr1_id == in_id)
            & (db.exchg_pair_bases.curr2_id == out_id)
              ).select().first()
    avg = pair and pair.hard_price
    if avg:
        # если задан жесткий курс а не с биржии то
        avg = float(avg)
        b = avg*0.99
        s = avg*1.01
        return b, s, avg
    
    field =  "AVG(sp1) AS s, AVG(bp1) AS b "

    if expired:
        cond = "curr1_id=%s AND curr2_id=%s AND on_update > '%s'" % (in_id, out_id, expired)
    else:
        cond = "curr1_id=%s AND curr2_id=%s" % (in_id, out_id)

    qry ="SELECT " + field + \
 " FROM exchg_pairs \
 WHERE (%s) \
 GROUP BY curr1_id, curr2_id \
 ;" % cond
    #print qry
    rec = db.executesql(qry, as_dict=True)
    #print rec
    if len(rec)>0:
        rec = rec[0]
        b = s = avg = None
        if 'b' in rec: b = rec['b']
        if 's' in rec: s = rec['s']
        # если одно из низ ноне
        if b and s:
            avg = (b+s)/2
            return float(b), float(s), float(avg)
    return None, None, None

def get_average_rate_bsa_2(db, in_id, out_id, expired):
    if in_id == out_id: return 1,1,1
    b=s=avg=None
    b,s,avg = get_average_rate_bsa_1(db, in_id, out_id, expired)
    if not b or not s:
        # поробуем обратный найти поиск
        b,s, avg = get_average_rate_bsa_1(db, out_id, in_id, expired)
        if b and s:
            b = 1/b
            s = 1/s
            avg = 1/avg
    return b,s,avg

# :: /bill/pay
# :: /default/currs
# :: db_client.get_xcurrs_for_shop
def get_average_rate_bsa(db, in_id, out_id, expired=None):
    if in_id == out_id: return 1,1,1
    # берем в расчет только недавние цены
    expired = expired or datetime.datetime.now() - datetime.timedelta(0,RATES_TIME)

    b,s,avg = get_average_rate_bsa_2(db, in_id, out_id, expired)
    if b and s:
        b,s = add_tax(db, in_id, out_id, b, s)
        return b, s, avg

    # иначе попробуем взять через кросскурс
    xcurr_in = db(db.xcurrs.curr_id == in_id).select().first()
    if xcurr_in:
        # это криптовалюта ее через кросскурс к биткоину
        cross1, x, e = db_common.get_currs_by_abbrev(db,'BTC')
    else:
        # это фиат - ее через кроссурс к доллару
        cross1, x, e = db_common.get_currs_by_abbrev(db,'USD')
    b1,s1,avg1 = get_average_rate_bsa_2(db, in_id, cross1.id, expired)
    #print 'b1,s1,avg1 -> cross1', b1,s1,avg1

    xcurr_out = db(db.xcurrs.curr_id == out_id).select().first()
    if xcurr_out:
        # это криптовалюта ее через кросскурс к биткоину
        cross2, x, e = db_common.get_currs_by_abbrev(db,'BTC')
    else:
        # это фиат - ее через кроссурс к доллару
        cross2, x, e = db_common.get_currs_by_abbrev(db,'USD')
    b2,s2,avg2 = get_average_rate_bsa_2(db, cross2.id, out_id, expired)
    #print 'cross2 -> b2,s2,avg2', b2,s2,avg2
    
    if b1 and s1 and b2 and s2:
        # нашли кросскурс
        # незабудем взять курс между USD <-> BTC
        b3,s3,avg3 = get_average_rate_bsa_2(db, cross1.id, cross2.id, expired)
        if not avg3:
            # курс между долларом и биткоином не найден
            return None, None, None
        #print 'cross1 -> cross2 b3,s3,avg3', cross1.abbrev, cross2.abbrev, b3,s3,avg3
        b, s = add_tax(db, in_id, out_id, b1*b2*b3, s1*s2*s3)
        return b, s, avg1*avg2*avg3
    return None, None, None


#################
## вычисление по степени объема а не по стакану биржи ##################
#############################################################################
# rate_rev - для взятия пообратному курсу
def get_pow_rate_par_1(db, curr_in, curr_out, rate_rev):
    if curr_in.id == curr_out.id: return [100000, 0]
    # ищем прямой курс
    rate_par = db((db.exchg_pair_bases.curr1_id==curr_in.id)
                        & (db.exchg_pair_bases.curr2_id==curr_out.id)
                        ).select().first()
    if rate_par:
        return [float(rate_par.base_vol), float(rate_par.base_perc)]

    # ищем обратный
    rate_par_rev = db((db.exchg_pair_bases.curr1_id==curr_out.id)
                        & (db.exchg_pair_bases.curr2_id==curr_in.id)
                        ).select().first()
    if rate_par_rev:
        # перевернем кол-во по курсу
        return [float(rate_par_rev.base_vol)/rate_rev, float(rate_par_rev.base_perc)]
    return
    
# :: get_best_rates
def get_pow_rate_par(db, curr_in, curr_out, rate_rev, expired):
    if curr_in.id == curr_out.id: return [100000, 0]
    
    rate_par = get_pow_rate_par_1(db, curr_in, curr_out, rate_rev)
    if rate_par:
        return rate_par

    # иначе попробуем взять через кросскурс
    xcurr1 = db(db.xcurrs.curr_id == curr_in.id).select().first()
    if xcurr1:
        # это криптовалюта ее через кросскурс к биткоину
        cross1, x, e = db_common.get_currs_by_abbrev(db,'BTC')
    else:
        # это фиат ее через кросскурс к доллару
        cross1, x, e = db_common.get_currs_by_abbrev(db,'USD')
        
    pr_b1, pr_s, pr_avg = get_average_rate_bsa(db, curr_in.id, cross1.id, expired)
    rate_par1 = get_pow_rate_par_1(db, curr_in, cross1, pr_b1)
    #print 'rate_par1:',rate_par1, pr_b1

    xcurr2 = db(db.xcurrs.curr_id == curr_out.id).select().first()
    if xcurr2:
        # это криптовалюта ее через кросскурс к биткоину
        cross2, x, e = db_common.get_currs_by_abbrev(db,'BTC')
    else:
        # это фиат ее через кросскурс к доллару
        cross2, x, e = db_common.get_currs_by_abbrev(db,'USD')
    pr_b2, pr_s, pr_avg = get_average_rate_bsa(db, cross2.id, curr_out.id, expired)
    rate_par2 = get_pow_rate_par_1(db, cross2, curr_out, pr_b2) # курс для <-БТС берем
    #print 'rate_par2:',rate_par2, pr_b2

    if rate_par1 and rate_par2:
        # нашли кросскурс
        pr_b3, pr_s, pr_avg = get_average_rate_bsa(db, cross1.id, cross2.id, expired)
        rate_par3 = get_pow_rate_par_1(db, cross1, cross2, pr_b3)
        #return [(rate_par1[0]*rate_par2[0]*rate_par3[0]/pr_b1/pr_b2/pr_b3)**0.5, rate_par1[1]+rate_par2[1]+rate_par3[1]]
        return [rate_par1[0], rate_par1[1]+rate_par2[1]+rate_par3[1]]

# :: /api/rates/
# :: orders_lib.inputs_update -> add_limit
# :: shops_lib.bills_draw_insert
# один раз для блока берем курсы валют чтобы сразу их учесть
def get_best_rates(db, curr_in, b_s=None, expired=None):
    rates = {}
    if not curr_in.used: return rates
    
    expired = expired or datetime.datetime.now() - datetime.timedelta(0, RATES_TIME)
    for curr_out in db(db.currs.used==True).select():
        if curr_out.id == curr_in.id:
            rates[curr_out.id] = [100000,0,1]
        else:
            #print curr_in.abbrev,'->',curr_out.abbrev, '==========================================='
            pr_b, pr_s, pr_avg = get_average_rate_bsa(db, curr_in.id, curr_out.id, expired)
            #print pr_b, pr_s, pr_avg, '======================================'
            if b_s:
                rate = pr_s
            else:
                rate = pr_b
            if rate:
                rate_par = get_pow_rate_par(db, curr_in, curr_out, rate, expired)
                #print 'rate_par', rate_par
                rates[curr_out.id] = [rate_par[0], rate_par[1], rate]

    return rates

# :: shops_lib.bills_draw_insert

# на входе нужен список курсов:
# best_rates = { 'curr1': { 'curr2':[base_vol, base_perc, base_rate] } }
# best_rates = { 'BTC': { 'BTC':[1, 0, 1] } } # здесь всегда 1 будет
# best_rates = { 'BTC': { 'LTC':[0.1, 0.5, 0.033] } } # за <0.1 БТС 0,5% за 0,3 - 1%; 0,9-1,5%; 2.7-2%
# best_rates = { 'BTC': { 'RUB':[0.1, 0.4, 30000] } } # за <0.1 БТС 0,4% за 0,3 - 0.8%; 0,9-1,2%; 2.7-1.6%
def get_best_rate(best_rates, curr_out, amo):
    rate_pars = best_rates.get(curr_out.id)
    if not rate_pars:
        #log( 'not base rate in db.exchg_pair_bases for %s' % curr_out.abbrev )
        return 0
    base_vol = rate_pars[0] # объем базовый
    base_perc = rate_pars[1] # процент с объема
    base_rate = rate_pars[2] # процент с объема
    power_perc = 0
    for pow in range(0,10):
        power_perc = pow
        vol = base_vol*3**pow
        #print vol, amo
        if vol > amo:
            break
    power_perc = power_perc + 1
    perc = power_perc*base_perc
    #print 'POWER:', power_perc, ' ->:', perc,'%'
    best_rate = base_rate * (1 - perc*0.01)
    return best_rate

## :: get_amo_out
# ищем заказ на курс, попути удаляем если он просрочен
# заказов может быть много и платежей разных - списком
def get_rate_order_for_trans(db, shop_order_addr_id, amo):
    dt_order = datetime.datetime.now() - datetime.timedelta(0, ORDER_TIME)
    ro = None
    amo = float(amo)
    for r in db((db.rate_orders_stack.ref_id == db.rate_orders.id)
                & (db.rate_orders.ref_id == shop_order_addr_id)
                ).select(orderby=~db.rate_orders_stack.created_on):
        if r.rate_orders_stack.created_on < dt_order:
            # заказ на курс просрочен
            del db.rate_orders_stack[r.rate_orders_stack.id]
            continue

        # проверим сколько уже использовано по заказу
        used_amo = float(r.rate_orders.used_amo or 0)
        print 'get_rate_order_for_trans - used_amo:', used_amo, 'amo:', amo
        if used_amo + amo > float(r.rate_orders.volume_in)*2.0:
            # добавим 100% к величине счета на случай переплаты
            # для счетов с ценой это не актуально - лишняя часть все равно вернется
            continue
        r.rate_orders.update_record(used_amo = used_amo + amo)
        print 'get_rate_order_for_trans  r.rate_orders:',  r.rate_orders
        return r.rate_orders
    return None

# :: orders_lib.inputs_update - amo for curr_in
# :: get_rate - amo for curr_in
# надо взять курс или с заказа на обмен или по объему с бирж
# а если нету то взять курс вычесленный по степени от объема
def get_amo_out(db, rates, shop_order_addr, curr_out, amo, created_on):
    if not curr_out.used: return None, None, None
    
    amo = float(amo)
    amo_out = rate_order = None
    # если время транзакции не поздно, тогда только заказ на обмен используем
    dt_trans = datetime.datetime.now() - datetime.timedelta(0, TRANS_TIME)
    if created_on and created_on > dt_trans:
        # тут же найдем заказ на курс для данной транзакции
        rate_order = shop_order_addr and get_rate_order_for_trans(db, shop_order_addr.id, amo) or None
        #print 'RATE by rate_order:',rate_order
    if rate_order:
        rate = float(rate_order.volume_out / rate_order.volume_in)
        amo_out = rate * amo
    else:
        #print 'RATES:', rates
        rate = get_best_rate(rates, curr_out, amo)
        if rate:
            amo_out = rate * amo
    return amo_out, rate_order, rate

# :: /bill/pay -- amo for curr_in
# :: db_client.get_xcurrs_for_shop
# надо взять курс или с заказа на обмен или по объему с бирж
# а если нету то взять курс вычесленный по степени от объема
# amo - vol_in !!! in /bill/pay
def get_rate(db, curr_in, curr_out, amo, created_on=None, shop_order_addr=None):
    if curr_in.id == curr_out.id:
        return amo, None, 1.0
    #print '%s[%s] -> [%s]' % (amo, curr_in.abbrev, curr_out.abbrev)
    rates = get_best_rates(db, curr_in)
    #print amo, rates
    
    return get_amo_out(db, rates, shop_order_addr, curr_out, amo, created_on)

# :: shops_lib.insert_shop_trans_order
def conv_pow(db, curr1, amo, curr2):
    rates = get_best_rates(db, curr1) # загодя возьмем курсы обмена для этой крипты
    rate = get_best_rate(rates, curr2, amo)
    #print 1/rate, rate
    return float(amo) * rate


################################################
## return par_base or pair_base_id if inserted
def set_rate_base_ecurr(db, abbrev, curr, rate, abbrev_out='USD', exchg_name='Yahoo', tax = 1,
                        curr_out=None, exchg = None):
    #print rate
    if curr:
        curr_id = curr.id
    else:
        # добавим
        curr_id = db.currs.insert(name = abbrev, abbrev=abbrev, used=True, name2=abbrev)
        db.ecurrs.insert(curr_id=curr_id)
    
    curr_out = curr_out or db(db.currs.abbrev==abbrev_out).select().first()
    if not curr_out:
        mess = 'curr_usd NOT FOUND: %s' % curr_out
        print mess
        return { 'error': mess }, None
    curr_out_id = curr_out.id
    
    exchg = exchg or db(db.exchgs.name==exchg_name).select().first()
    if exchg:
        exchg_id = exchg.id
    else:
        exchg_id = db.exchgs.insert( name = exchg_name, used = True, tax = tax, API_type='fiat')

    pair = db((db.exchg_pairs.exchg_id==exchg_id)
                & (db.exchg_pairs.curr1_id==curr_id)
                & (db.exchg_pairs.curr2_id==curr_out_id)
                ).select().first()
    if pair:
        pair.update_record(sp1 = rate, bp1 = rate, on_update=datetime.datetime.now())
    else:
        db.exchg_pairs.insert( exchg_id = exchg_id, used = True,
           curr1_id = curr_id, curr2_id = curr_out_id,
           sp1 = rate, bp1 = rate)
    
    base_vol = 100/rate
    pair = db((db.exchg_pair_bases.curr1_id==curr_id)
                & (db.exchg_pair_bases.curr2_id==curr_out_id)).select().first()
    if pair:
        pair.update_record(on_update=datetime.datetime.now(),
           base_vol = base_vol, base_perc=0.3)
        return None, pair
    else:
        pair_id = db.exchg_pair_bases.insert( curr1_id = curr_id, curr2_id = curr_out_id,
           base_vol = base_vol, base_perc=0.3)
        return None, db.exchg_pair_bases[pair_id]
