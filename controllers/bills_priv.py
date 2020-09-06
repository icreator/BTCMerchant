# coding: utf8

import common
# запустим сразу защиту от внешних вызов
#print request.function
#if request.function not in ['list', 'download'] and common.not_is_local(): raise HTTP(200, T('ERROR'))
if common.not_is_local(): raise HTTP(200, T('ERROR'))

#import datetime
#import json

#import db_common
#import db_client

#############################################
def last():
    so = db(((db.shop_orders.payed_soft>0) | (db.shop_orders.payed_hard>0) | (db.shop_orders.payed_true>0))
            & (db.shop_orders.price>0)).select(orderby=~db.shop_orders.id, limitby=(0, 20))
    tab = CAT()
    for r in so:
        sh = db.shops[r.shop_id]
        cr = db.currs[r.curr_id]
        tab += DIV(
            sh.url or sh.name,' ',
            r.payed_soft + r.payed_hard + r.payed_true,
            cr.abbrev
            )
    return tab
