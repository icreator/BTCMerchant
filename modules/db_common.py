#!/usr/bin/env python
# coding: utf8

# http://web2py.com/examples/static/epydoc/web2py.gluon.dal-module.html

#from datetime import datetime, timedelta
from datetime import datetime
from decimal import Decimal

'''
from gluon.dal import DAL, Field, Table
db = DAL("sqlite://storage.sqlite",
        #pool_size=1, 
        #check_reserved=['all'],
# this keyword buil model on fly on load
        auto_import=True,
        folder="../databases")
#print db.tables
'''
def get_shop_order(db, shop, order_id):
    shop_order = db((db.shop_orders.shop_id==shop.id)
        & (db.shop_orders.order_id==order_id)).select().first()
    return shop_order


def get_currs_by_abbrev(db, abbrev, curr=None):
    curr = curr or db(db.currs.abbrev==abbrev).select().first()
    xcurr = curr and db(db.xcurrs.curr_id==curr.id).select().first()
    ecurr = curr and db(db.ecurrs.curr_id==curr.id).select().first()
    return curr, xcurr, ecurr
def get_currs_by_addr(db, addr, abbev_out=None, cc=None):
    if not addr or not len(addr)>30: return None, None, None
    abbrev = None
    ch = addr[0:1]
    if ch == '1' or ch == '3': abbrev = 'BTC'
    elif ch == 'C': abbrev = 'CLR'
    elif ch == 'L': abbrev = 'LTC'
    elif ch == '4': abbrev = 'NVC'
    if cc:
        from crypto_client import is_not_valid_addr
        if is_not_valid_addr(cc, addr): return
    if abbev_out: return abbrev
    return get_currs_by_abbrev(db, abbrev)

def get_shop_name(shop): return shop.name or shop.url or shop.mail

# статитстика по среднему курсу обмена
def currs_stats_update(db, curr_id, deal_id, volume_out):
    currs_stats = db((db.currs_stats.curr_id==curr_id)
        & (db.currs_stats.deal_id==deal_id)).select().first()
    if not currs_stats:
        db.currs_stats[0] = {
            'curr_id': curr_id,
            'deal_id': deal_id,
            'average': volume_out,
            'count': 1,
            }
    else:
        average = currs_stats.average or 0
        count = currs_stats.count or 0
        volume_out = Decimal( volume_out )
        currs_stats.average = count/(count + 1)*average + volume_out/(count + 1)
        currs_stats.count = count + 1
        currs_stats.update_record()


def get_exchg_pairs(db,id):
    return db(db.exchg_pairs.exchg_id==id).select()

#def commit(): db.commit()
        
def get_limits(db, exchg_id, curr_id):
    limits = db((db.exchg_limits.exchg_id==exchg_id) & (db.exchg_limits.curr_id==curr_id)).select().first()
    #print limits
    return limits

def get_reserve(curr, negative=None):
    #print type(curr.balance), type(curr.deposit), type(curr.shops_deposit), type(curr.fee_out)
    b = Decimal(curr.balance) - curr.deposit - curr.shops_deposit - Decimal(curr.fee_out)
    if not negative and b < 0: b = Decimal(0)
    return b
# баланс который для выплаты магазинам подходит
def get_shops_reserve(curr):
    #print type(curr.balance), type(curr.deposit), type(curr.fee_out)
    b = Decimal(curr.balance) - curr.deposit - Decimal(curr.fee_out)
    if b < 0: b = Decimal(0)
    return b

def store_rates(db, pair, sell, buy):
    pair.update_record(sp1 = sell, bp1 = buy, on_update = datetime.now())

def store_depts(db, pair, rec):
    #print rec
    pair.sp1=rec[0][0][0]
    pair.sv1=rec[0][0][1]
    pair.sp2=rec[0][1][0]
    pair.sv2=rec[0][1][1]
    pair.sp3=rec[0][2][0]
    pair.sv3=rec[0][2][1]
    pair.sp4=rec[0][3][0]
    pair.sv4=rec[0][3][1]
    pair.sp5=rec[0][4][0]
    pair.sv5=rec[0][4][1]
            
    pair.bp1=rec[1][0][0]
    pair.bv1=rec[1][0][1]
    pair.bp2=rec[1][1][0]
    pair.bv2=rec[1][1][1]
    pair.bp3=rec[1][2][0]
    pair.bv3=rec[1][2][1]
    pair.bp4=rec[1][3][0]
    pair.bv4=rec[1][3][1]
    pair.bp5=rec[1][4][0]
    pair.bv5=rec[1][4][1]

    #pair.update()
    pair.on_update = datetime.now()
    pair.update_record()
    db.commit()
    #print pair.uniq, "updated..."
