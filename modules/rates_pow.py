#!/usr/bin/env python
# -*- coding: utf-8 -*-
#from gluon import *

def get_bill_rate(rate_pars, amo_out):
    base_vol = rate_pars[0] # объем базовый
    base_perc = rate_pars[1] # процент с объема
    base_rate = rate_pars[2] # курс обмена
    amo_in = amo_out * base_rate
    power_perc = 0
    for pow in range(0,10):
        power_perc = pow
        vol = base_vol*3**pow
        if vol > amo_in:
            break
    power_perc = power_perc + 1
    perc = power_perc*base_perc
    #print 'POWER:', power_perc, ' ->:', perc,'%'
    return base_rate * (1 + perc*0.01)

    
# not_used - список запрещенных валют для клиентов или магазинов
# only_used - список только используемых валют
def get_bill_rates(db, volume_out, curr_out, shop, not_used=None, only_used=None):
    curr_out_id = curr_out.id

    from applications.shop.modules.rates_lib import get_best_rates
    # возмем все что есть к обмену по цене продажи а не покупки
    rates = get_best_rates(db, curr_out, True)
    # теперь по всем криптам пройдемся и если нет в парах то
    # значит запрет в форме сделаем
    pairs = {}
    for (curr_in_id, tab) in rates.iteritems():
        curr_in = db.currs[curr_in_id]
        if not_used and curr_in.abbrev in not_used: continue
        if only_used and curr_in.abbrev not in only_used: continue

        if curr_in.id == curr_out.id:
            add_change = 0 # добавка на изменение курса - клиент приплачивает а мы ему сдачу потом при точном расчете курса
            rate = 1
        else:
            add_change = curr_in.add_change or 3
            #print curr_in.abbrev, '->', curr_out.abbrev
            #rate = conv_pow(db, curr_in, volume_in, curr_out)
            rate = get_bill_rate(tab, volume_out)
            #print rate

        pairs[curr_in_id] = {
                  'rate': rate,
                  'curr': curr_in,
                  'add_change': add_change,
                }

    return pairs
