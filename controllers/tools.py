# coding: utf8
import common
# запустим сразу защиту от внешних вызов
if common.not_is_local(): raise HTTP(200, T('ERROR'))

import sys
import time
import crypto_client

from decimal import Decimal
import datetime
#import json

def log(mess):
    print mess
    db.logs.insert(mess='CNT: %s' % mess)
def log_commit(mess):
    log(mess)
    db.commit()


def del_logs():
    db.logs.truncate()
def del_startup():
    #db.startup.truncate()
    pass

def clients_auto_collect():
    import clients_lib
    clients_lib.auto_collect(db)

def  get_reserve():
    if len(request.args) == 0:
        mess = 'len(request.args)==0'
        print mess
        return mess
    #import db_client
    import db_common
    import crypto_client
    curr, xcurr, e = db_common.get_currs_by_abbrev(db,request.args[0])
    if not xcurr: return 'xcurr not found'
    cn = crypto_client.conn(curr, xcurr)
    if not cn: return 'xcurr not connected'
    return crypto_client.get_reserve(curr, xcurr, cn) or 'None'

def  sender_addrs():
    if len(request.args) < 2:
        mess = 'len(request.args) <2 /BTC/txid'
        print mess
        return mess
    #import db_client
    import db_common
    import crypto_client
    curr, xcurr, e = db_common.get_currs_by_abbrev(db,request.args[0])
    if not xcurr: return 'xcurr not found'
    cn = crypto_client.conn(curr, xcurr)
    if not cn: return 'xcurr not connected'
    return BEAUTIFY(crypto_client.sender_addrs(cn, request.args[1], with_amo=True))

# http://127.0.0.1:8000/shop/tools/sender_addr/BTC/608a98be99be319bc6d024aa56758f1199700ee480424964c73d830eb9f12e18
# берет тот адрес из всех входов с котрого максим приход был
def  sender_addr():
    if len(request.args) < 2:
        mess = 'len(request.args) <2 /BTC/txid'
        print mess
        return mess
    #import db_client
    import db_common
    import crypto_client
    curr, xcurr, e = db_common.get_currs_by_abbrev(db,request.args[0])
    if not xcurr: return 'xcurr not found'
    cn = crypto_client.conn(curr, xcurr)
    if not cn: return 'xcurr not connected'
    return BEAUTIFY(crypto_client.sender_addr(cn, request.args[1]))


def try_make_note_url():
    if len(request.args) == 0:
        mess = 'len(request.args)==0'
        print mess
        return mess
    import shops_lib
    shop_order = db.shop_orders[request.args[0]]
    shop = db.shops[shop_order.shop_id]
    return shops_lib.try_make_note_url(db, shop, shop_order, None)
def try_make_note_url_cmd():
    if len(request.args) == 0:
        mess = 'len(request.args)==0'
        print mess
        return mess
    import shops_lib
    cmd = db.shops_cmds[request.args[0]]
    shop = db.shops[cmd.shop_id]
    return shops_lib.try_make_note_url(db, shop, None, cmd)
def test_shop_notify():
    if len(request.args) == 0:
        mess = 'len(request.args)==0'
        print mess
        return mess
    import shops_lib
    note = db.shop_orders_notes[request.args[0]]
    res = note and shops_lib.notify_one(db, note) or 'note deleted'
    return res
# TODO
## сделать это в меню в тулсы

def pay_ins_add_to_stack():
    if len(request.args) == 0: return '/txid'
    txid = request.args(0)
    pay_in = db(db.pay_ins.txid == txid).select().first()
    if not pay_in: return 'not found pay_in - txid'
    r = db(db.pay_ins_stack.ref_id == pay_in.id).select().first()
    if r: return 'already added'
    soa = db.shop_order_addrs[ pay_in.shop_order_addr_id]
    db.pay_ins_stack.insert( ref_id = pay_in.id, xcurr_id = soa.xcurr_id )
    return 'added'

# tools/proc_unspent/BTC/23/15tMgyVkqvQbAk43nNS86PSwVVwv35DtCY
# b_p_proc_unspent( db, conn, curr, xcurr, conf=None, addr_in=None )
def proc_unspent():
    if len(request.args) == 0:
        mess = 'len(request.args)==0'
        print mess
        return mess
    #import db_client
    import db_common
    import serv_block_proc
    import crypto_client
    curr, x, e = db_common.get_currs_by_abbrev(db,request.args[0])
    if not x: return 'xcurr not found'
    cn = crypto_client.conn(curr,x)
    if not cn: return 'xcurr not connected'
    conf_from = int (request.args(1) or 2)
    addr_in = request.args(2)
    vol = None
    tab, summ = crypto_client.get_unspents(cn, conf_from, vol, addr_in and [addr_in] or None, None, x)
    tab2 = serv_block_proc.b_p_proc_unspent( db, cn, curr, x, conf_from, addr_in)
    for r in tab:
        r['dt'] =  '%s' % datetime.datetime.fromtimestamp(r['time'])
        pay_in = db(db.pay_ins.txid == r['txid']).select().first()
        r['pay_ins'] = pay_in and {'id': pay_in.id, 'status': pay_in.status,
                       'amount': pay_in.amount, 'amo_out': pay_in.amo_out,
                        'amo_ret': pay_in.amo_ret } or '!!! NONE !!!'
    tab = sorted(tab, key=lambda r: r['dt'], reverse=True)
    summ2 = Decimal(0)
    for r in tab2:
        r['dt'] =  '%s' % datetime.datetime.fromtimestamp(r['time'])
        pay_in = db(db.pay_ins.txid == r['txid']).select().first()
        r['pay_ins'] = pay_in and {'id': pay_in.id, 'status': pay_in.status,
                       'amount': pay_in.amount, 'amo_out': pay_in.amo_out,
                       'amo_ret': pay_in.amo_ret } or '!!! NONE !!!'
        summ2 += r['amo']
    tab2 = sorted(tab2, key=lambda r: r['dt'], reverse=True)
    tab3 = ['unspents from 0 to %s +Generate +%s' % (conf_from, x.conf_gen),
            'count: %s' % len(tab2), summ2, tab2,
            '*****************', 'unspents from %s to 999999 +generate' % conf_from,
            'crypto_client.get_unspents:',
            'count: %s' % len(tab), summ ,tab]
    cn.close()
    return BEAUTIFY(tab3)

def retrans_rawtr():
    import crypto_client
    for xcurr in db(db.xcurrs).select():
        curr = xcurr.curr_id and db.currs[xcurr.curr_id]
        if not curr: continue
        cn = crypto_client.conn(curr,xcurr)
        if not cn: continue
        crypto_client.re_broadcast(db,curr,xcurr,cn)

# если транзакция была создана но в сеть не отправилась - повторить отравку
# only_get_confs - False для отправки
def bills_draws_trans_re_broadcast():
    import crypto_client
    only_get_confs = True
    only_get_confs = False
    for xcurr in db(db.xcurrs).select():
        curr = xcurr.curr_id and db.currs[xcurr.curr_id]
        if not curr:
            print 'not in curr', xcurr.curr_id
            continue
        if not curr.used: continue
        cn = crypto_client.conn(curr,xcurr)
        if not cn:
            print 'not connection to', curr.abbrev
            continue
        crypto_client.re_broadcast_bills_draws_trans(db,curr,xcurr,cn, only_get_confs)


# depth/1/ltc_rub = "UpBit ic"
# depth/2/ltc_rur - "BTC-e ic"
def depth():
    if len(request.args) == 0:
        mess = 'len(request.args)==0'
        print mess
        return mess
    import exch_client
    exchg = db.exchgs[request.args[0]]
    pair = request.args[1]
    exch_client.conn(exchg)
    sells, pays = exch_client.depth(exchg.name, pair)
    exch_client.conn_close(exchg)
    return dict(sells=sells, buy=pays)


# по отловленным входам
# сделать платежи фиата
def to_pay():
    print 'to_pay'
    from serv_to_pay import run_once
    run_once(db)

############################################
# ВНИМАНИЕ! эта страница вызывается из клиентов-кощельков
# по адресу на портал
# start /B /LOW /MIN curl http://127.0.0.1:8000/shop/tools/block_proc/%1 -s >>!notify_log.txt
# args:
# tools/block_proc/LTC
# http://127.0.0.1:8000/shop2/tools/block_proc/CLR/92000/15tMgyVkqvQbAk43nNS86PSwVVwv35DtCY
def block_proc():
    session.forget(response)
    if len(request.args) == 0:
        mess = 'len(request.args)==0'
        print mess
        return mess
    import serv_block_proc
    abbrev = request.args[0]
    from_block = int(request.args(1) or 0)
    addr_in = request.args(2)

    print '\n\n block_proc', abbrev, from_block, addr_in
    #### ВНИМАНИЕ - если задан БЛОК - то все возвраты продублируются!!!
    #run_once(db, abbrev, from_block_in=None, addr_in=None, conn=None, curr=None, xcurr=None, not_ret=None)
    # NOT_RETURN = True
    serv_block_proc.run_once(db, abbrev, from_block, addr_in, None, None, None, True)

###
### обновить статусы входов - вызывается из block_proc - если есть новый блок
### тоесть обработать только записи уже из ббазы 
def inputs_update():
    if len(request.args)==0: return '/CURR/from_block'
    import db_common
    import crypto_client
    curr, xcurr, ecurr = db_common.get_currs_by_abbrev(db, request.args(0))
    if not curr or not xcurr: raise HTTP(503, 'ERROR: xcurr [%s] not found' % request.args[0] )
    conn = crypto_client.conn(curr,xcurr)
    if not conn: return ' not connet'
    curr_block = int(request.args(1) or xcurr.from_block)
    import orders_lib
    res = orders_lib.inputs_update(db, curr_block, curr, xcurr, conn)
    return '<br><br><br> %s<br> %s' % (curr_block, res)
    
# отправить на апбит Розе и Ис ларки
# http://127.0.0.1:8000/ipay8/tools/send_to_many/CLR?CGk6Q3cx7qNEzAoWx2YnMNm2xvTQKEaYun=0.1&CdYGrbTZNhgYKh5gghYY6mFWr9pmGbEedY=0.13
# http://127.0.0.1:8000/ipay8/tools/send_to_many/LTC?Lc7nSnWdhp1RU9kCDZS8gRCV1WBAMupkYy=0.01
# Lc7nSnWdhp1RU9kCDZS8gRCV1WBAMupkYy
# vars: {addr=amount, ...}
def send_to_many():
    import db_common
    import crypto_client
    curr, xcurr, ecurr = db_common.get_currs_by_abbrev(db, request.args[0])
    if not curr or not xcurr: raise HTTP(503, 'ERROR: xcurr [%s] not found' % request.args[0] )

    if not request.vars or len(request.vars)==0: HTTP(500, 'list ={}' )

    res = crypto_client.send_to_many(curr, xcurr, request.vars)
    print res
    return '%s' % res



def send_to_main(conn, acc_from, amo):
    main_addr = crypto_client.get_xaddress_by_label(conn,'.main.')
    mess = "to send %s from acc:"% amo +acc_from +" to " + main_addr
    print 'try', mess
    try:
        conn.sendfrom( acc_from, main_addr,amo)
    except Exception as e:
        if e.error['code']==-4:
            # если не хватает на комисиию то уменишим сумму и повторим
            print 'tax -0.01'
            send_to_main(conn, acc_from, amo-0.01)
            return
        print e.error
        return e.error
    #print mess


# инициализация портала
def inits_new_portal(dd):
    return
    db.to_phone.drop()
    resp = ""
    # для всех криптовалют создадим главные аккоунты в кошельках
    for xcurr in db(db.xcurrs).select():
        try:
            aa = crypto_client.conn(xcurr)
        except Exception as e:
            print e
            msg = xcurr.name + " no connection to wallet"
            print msg
            resp = resp + msg + '<br>'
            continue

        try:
            x = crypto_client.get_xaddress_by_label(xcurr,'.main.',aa)
        except Exception as e:
            print e
            msg = xcurr.name + " no made .main. account"
            print msg
            resp = resp + msg + '<br>'
            continue


    return resp


    
def run_notes():
    import serv_notes
    return serv_notes.run_once(db)

def withdraw():
    if len(request.args) == 0:
        mess = 'len(request.args)==0 - [BTC]'
        return mess
    import db_common
    import shops_lib
    import crypto_client
    curr, xcurr, e = db_common.get_currs_by_abbrev(db,request.args[0])
    conn = crypto_client.conn(curr,xcurr)
    shops_lib.withdraw(db, curr, xcurr, conn, curr.withdraw_over) # тут может крипты не хватить так как обмен нужен еще

def set_addrs():
    bill_id = 188
    return 'stop'
    addrs = { "14qZ3c9WGGBZrftMUhDTnrQMzwafYwNiLt": 1197,
        "14pv2yaMYv8bYfMkJ1pYggyjQheeHAtmv9": 60,
        "195s2FScWRTLyexqqCZUVQGg895vdp77ne": 100,
        "1KkCVfQxVFJx2BqKZnTjFRTTZU3L2wmGc9": 1,
        "1Lrjrvv3kK3n7ZeJ1ibAtPUa8Q8LTdwPvB": 1,
        "12oqAy1nPPRoDn48eCHhQa5ZFKfyH7hh5v": 12,
        "1Ba8hRx33oU1bNrdfoHW9WKAA2eH1NpneT": 31,
        "1AYT5BuAUQDjDRRK34DaZnYAM7Dv92DNm4": 1,
        "1HNNdXyagnu1n5NDhmnEGNa22xTaunL6Wb": 8,
        "1Bqf3uTd2oT8WftjnAkktyAuzdPH7zRcEp": 4
        }
    bill = db.shop_orders[bill_id]
    bill.update_record( addrs = addrs )
    return '%s' % bill.addrs

def cmds_run():
    import serv_cmds
    return serv_cmds.run(db)

# tools/hexf/12/345
def hexf():
    import base64, os
    s = os.urandom(6)
    r = base64.b64encode(s, '_-')[:8]
    print r
    return s

# если записи из стека ушли не пройдя до TRUE то вернем их
def pay_ins_return_to_stack():
    hh = CAT()
    return 'skiip'
    for r in db(db.pay_ins.status=='NEW').select():
        st = db(db.pay_ins_stack.ref_id == r.id).select().first()
        if st: continue
        shop_order_addr = db.shop_order_addrs[r.shop_order_addr_id]
        db.pay_ins_stack.insert(ref_id = r.id, xcurr_id = shop_order_addr.xcurr_id, in_block = r.in_block )
        hh += DIV('ref_id = ', r.id, '  xcurr_id = ', shop_order_addr.xcurr_id, '  in_block = ', r.in_block)
    return hh

## shop/tools/wager_solve_one/[wager_stack_id]
def wager_solve_one():
    #    tr_info = conn.getrawtransaction(tr,1)

    if len(request.args) == 0:
        mess = 'len(request.args)==0 - [wagers_stack]'
        return mess
    
    wager_stack = db.wagers_stack[ request.args[0] ]
    if not wager_stack: return 'wager_stack not exist'
    wager = db.wagers[ wager_stack.ref_id ]
    if not wager: return 'wager not exist'
    
    curr = db.currs[ wager.curr_id ]
    xcurr = curr and db( db.xcurrs.curr_id == curr.id ).select().first()
    if not xcurr: return ' xcurr not found'

    import crypto_client
    conn = crypto_client.conn(curr,xcurr)
    print conn
    tr_info = conn.getrawtransaction('wert',1)
    return dict(r = tr_info)

    import wager_lib
    return wager_lib.solve_one(db, curr, xcurr, conn, wager_stack)

def trans_exist():
    if len(request.args) == 0:
        mess = 'len(request.args)==0 - [CURR]/txid'
        return mess
    import db_common
    import shops_lib
    import crypto_client
    curr, xcurr, e = db_common.get_currs_by_abbrev(db,request.args[0])
    conn = crypto_client.conn(curr,xcurr)
    if not conn: return 'conn broken'
    return 'trans_exist %s' % crypto_client.trans_exist(conn, request.args[1])
