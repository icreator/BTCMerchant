#!/usr/bin/env python
# coding: utf8
from time import sleep
Test = None

from decimal import Decimal
import datetime
#from gluon import *
import urllib, urllib2
import httplib
import json

from common import rnd_8
import db_common, db_client
import crypto_client
import rates_lib

def log(db, l2, mess='>'):
    m = 'shops_lib'
    mess = '%s' % mess
    print m, l2, mess
    db.logs.insert(label123456789 = m, label1234567890 = l2, mess = mess)
def log_commit(db, l2, mess='>'):
    log(db, l2, mess)
    db.commit()

# если счет создан по адресу кошелька а не магазину, зарегистрированному у нас
# то создаем новый магазин (или старый)
def make_simple_shop(db, name, vars, noseek=False, curr=None, xcurr=None):
    if not noseek: shop = db(db.shops.name==name).select().first()
    #print shop
    if noseek or not shop:
        if not curr and vars.get('conv_curr'):
            # найдем по абривиатуре
            curr, xcurr, _ = db_common.get_currs_by_abbrev(db, vars['conv_curr'])
        if not xcurr:
            return
        # проверим на слэш в конце УРЛ - он мешает при уведомлении - удалим
        url = vars.get('shop_url')
        # от / не зависит if url[-1:] == '/': url = url[:-1]
        shop_id = db.shops.insert(name = name,
                     simple_curr = curr.id,
                     url =        url,
                     show_text =  vars.get('show_text'),
                     note_url =   vars.get('note_url'),
                     back_url =   vars.get('back_url'),
                     note_on =    vars.get('note_on'),
                     icon_url =   vars.get('icon_url'),
                     email =      vars.get('email'),
                     not_listed = True,
                     )
        shop = db.shops[shop_id]
        # и добавим адрес кошелька
        db.shops_xwallets.insert( shop_id = shop_id, xcurr_id = xcurr.id, addr = name )

    return shop

# используется при создании счета оплаты в make
def is_simple_shop(db, vars, shop_id):
    shop = None
    if len(shop_id) > 30:
        # это адрес криптовалюты куда выводить - тут магазин неизвестен
        curr, xcurr, _ = db_common.get_currs_by_addr(db, shop_id)
        if not xcurr:
            return None, None
        cc = crypto_client.conn(curr, xcurr)
        if not cc or crypto_client.is_not_valid_addr(cc, shop_id):
            return None, None
        # поиска магазина еще не было - False
        shop = make_simple_shop(db, shop_id, vars, False, curr, xcurr)
        if not shop:
            # мгазин не найден и не создан
            return None, None
        shop_id = shop.id
    elif not shop_id.isdigit():
        return None, None
    shop = shop or db.shops[shop_id]
    return shop, shop_id

def get_trans(db, shop, order_id):
    return db((db.shops_trans.shop_id == shop.id)
              & (db.shops_trans.order_id == order_id)).select()
def get_bal(db, shop, curr):
    xw = db((db.shops_balances.shop_id == shop.id)
            & (db.shops_balances.curr_id == curr.id)).select().first()
    return xw and xw.bal or None

def update_bal(db, shop, curr, amo, keep=None):
    xw = db((db.shops_balances.shop_id == shop.id)
            & (db.shops_balances.curr_id == curr.id)).select().first()
    if not xw:
        id = db.shops_balances.insert(
                shop_id = shop.id,
                curr_id = curr.id,
                bal = 0,
                kept = 0.0,
                )
        xw = db.shops_balances[id]

    curr.update_record(balance = Decimal(curr.balance) + Decimal(amo),
                       shops_deposit = Decimal(curr.shops_deposit) + Decimal(amo))
    print 'updated bal, shop_dep:', curr.abbrev, curr.balance, curr.shops_deposit

    amo_bal = Decimal(amo)
    amo_keep = Decimal(0)
    if keep and keep>0:
        if keep > 1: keep = Decimal(1)
        amo_keep = Decimal(amo) * Decimal(keep)
        amo_bal = Decimal(amo) - Decimal(amo_keep)
    xw.update_record(bal = xw.bal + Decimal(amo_bal), kept = xw.kept + Decimal(amo_keep))
    db.commit() # гаче там потом берется неизмененый баланс

    print 'updated bal, kept:', shop.url or shop.name, xw.bal, xw.kept

    return xw.bal

# счет с автовыплатами - создадим записи на выплаты по этому счету
# а на результате дадим остаток от KEEP для создания транзакции для магазина
# тоесть в автовыплатах учавствовать будет сумма не вся а та что в УДЕРЖАННЫЕ не входит
def bills_draw_insert(db, shop_order, curr, amo, desc):
    # сначала подсчет общего веса
    tab = shop_order.addrs
    vol = 0
    for (k,v) in tab.iteritems():
        v = float(v)
        vol += v
        tab[k] = v

    # теперь вычислим курсы обмена для данной крипты входа
    rates = rates_lib.get_best_rates(db, curr) # загодя возьмем курсы обмена для этой крипты
    amo = float(amo)

    # посмотрим что оставить магазину в резерв
    amo_keep = 0
    keep = shop_order.keep
    if keep and keep>0:
        if keep>1: keep = 1
        amo_keep = amo * float(keep)
        # новое АМО берем
        amo = amo - amo_keep

    for (addr, v) in tab.iteritems():
        amo_out = rnd_8( v/vol * amo)
        # найдем курс обмена
        curr2, x, e = db_common.get_currs_by_addr(db, addr)
        if curr2.id != curr.id:
            rate = rates_lib.get_best_rate(rates, curr2, amo_out)
            amo_out = rate * amo_out

        _id = db.bills_draws.insert(
            shop_order_id = shop_order.id,
            curr_id = curr2.id,
            addr = addr,
            amo = amo_out,
            )
    db.commit() # гаче там потом берется неизмененый баланс
    return Decimal(amo_keep)

# сюда приходит при смене статуса у заказа на выплату в баланс магазина
# amo - велична на которую надо увеличить баланс магазина
# но еслии у счета зананы дареса автовыплат - надо без изменения
# баланса у магазина сделать выплаты - как?
# тут нужен pay_in - все данные от входе на случай если
# для магазина не нужна конвертация входов - not_convert=1
# curr_pay_in=None, amo_pay_in=None - это неконвертированные значения входа и валюты
def insert_shop_trans_order(db, shop_order, amo, shop, curr, desc, curr_pay_in, amo_pay_in):
    if not shop:
        shop = db.shops[shop_order.shop_id]
    if not curr:
        curr = db.currs[shop_order.curr_id]

    log(db, 'insert_shop_trans_order', 'amo: %s bill: %s' % (amo,shop_order))

    # берем тут то что надо удержать - если будут автовыплаты то он станет = 1
    keep = shop_order.keep
    if shop_order.addrs:
        # если у счета есть адреса для авто выплат то создадим их
        # в транзакции магазина запишем результат транзакции
        # и остаток для удержания - keep, но для записи в балансы его сделаем keep =1
        # и баланс магазина  тоже не будем менять - там тогда баланс пересчитается с keep=1
        amo_keep = bills_draw_insert(db, shop_order, curr_pay_in, amo_pay_in, desc)
        desc = '%s: to auto send many' % desc
        # дальше баланс надо в остаток записать
        amo = amo_keep
        keep = 1
        #print 'shop_order.addrs is SET - new keep:', amo, keep, shop_order.addrs

    # продоложим с остатоком
    if amo and not shop_order.not_convert and shop_order.conv_curr_id:
        # если не запрещено конвертировать и есть валюта конвертации то
        conv_curr = db.currs[shop_order.conv_curr_id]
        conv_amo = rates_lib.conv_pow(db, curr, amo, conv_curr)
        #print 'convert to', conv_curr.abbrev, conv_amo
        curr = conv_curr
        amo = conv_amo

    shops_trans_id = db.shops_trans.insert(
        shop_order_id = shop_order and shop_order.id or None,
        curr_id = curr.id,
        amo = amo,
        desc_ = desc,
        )
    #print '%s[%s] inserted to SHOP %s' % (amo, curr.abbrev, shop.url or shop.id)
    shop.update_record( uses = (shop.uses or 0) + 1)
    # тут валюта и курс не понятен average = shop.average or Decimal

    # изменим баланс валют на счетах клиента
    # там же commit()
    update_bal(db, shop, curr, amo or 0, keep)
    db.commit() # гаче там потом берется неизмененый баланс
    return shops_trans_id

def insert_shop_trans_withdraw(db, shop, curr, amo, txfee, desc):
    # изменим баланс валют на счетах клиента
    bal = update_bal(db, shop, curr, -amo)
    shops_trans_id = db.shops_draws.insert(
        shop_id = shop.id,
        curr_id = curr.id,
        #amo = amo - txfee,
        amo = amo,
        desc_ = desc,
        )
    xcurr = db(db.xcurrs.curr_id == curr.id).select().first()
    xwallet = xcurr and db((db.shops_xwallets.shop_id == shop.id)
            & (db.shops_xwallets.xcurr_id == xcurr.id)).select().first()
    if xwallet:
        xwallet.update_record( payouted = xwallet.payouted + Decimal(amo) )

    db.commit()
    #print '%s[%s] withdrawed to SHOP %s' % (amo, curr.abbrev, shop.name or shop.url or shop.id)
    return shops_trans_id, bal

def try_make_note_url2(db, shop, shop_order, cmd, pars=None):
    note_url = shop.note_url
    if not note_url: return
    #print  shop_order, '\n', cmd
    try:
        #print note_url
        #if note_url[:0] == '/': note_url = note_url[1:]
        url_resp = '%s' % note_url
        #print url_resp

        if shop_order:
            pars0 = { 'bill': shop_order.id, 'order': shop_order.order_id }
        elif cmd:
            pars0 = { 'cmd': cmd.hash1 }
        else:
            pars0 = None
        #print pars0
        if pars:
            # добавим параметры еще к строке
            if pars0:
                pars0.update(pars)
            else:
                pars0 = pars
        url_resp = url_resp + urllib.urlencode(pars0)

        return url_resp
    except Exception as e:
        log(db, 'try_make_note_url2', 'ERROR make url_resp %s' % e)
        return

def try_make_note_url(db, shop, shop_order, cmd, pars=None):
    url_pars = try_make_note_url2(db, shop, shop_order, cmd, pars)
    if url_pars: return '%s%s' % (shop.url, url_pars)
    return

def notify_one_url(db, shop, shop_order, cmd=None):
    url_path = try_make_note_url2(db, shop, shop_order, cmd)
    if not url_path:
        return

    r = None
    timeout = 2
    host = shop.url
    try:
        f = urllib2.urlopen(host + '/' + url_path , None, timeout)
        r = f.getcode()
        #print 'resp_status:',r.status, r.reason
        return r
    except:
        log(db, 'notify_one', '%s/%s' % (host, url_path))
        pass
    return
#################################### OLD
'''
    #if host[-1:] == '/': host = host[:-1]
    #if host[-1:] != '/': host += '/'
    print 'try httplib.HTTPConnection(%s)' % host
    try:
        log(db, 'notify_one', '%s + %s' % (host, url_path))
        if host[0:7] == 'http://':
            host = host[7:]
            conn_ = httplib.HTTPConnection(host, None, None, timeout)
        elif host[0:8] == 'https://':
            host = host[8:]
            conn_ = httplib.HTTPSConnection(host, None, None, None, None, timeout)
        #print host, conn_
    except Exception as e:
        log(db, 'notify_one', 'ERROR: httplib.HTTPConnectio(%s) -> %s' % (host, e))
        return 'not connect - %s' % e
    #print 'try  conn_.request(%s)' % url_path
    try:
        # HTTPS апшет, а HTTP нет
        # error - 301, removed - значит там вместо HTTP HTTPS и надо задавать адрес магазина https://bitrent.in
        path = host + '/' + url_path
        print 'PATH:', path
        conn_.request('HEAD', path)
        r = conn_.getresponse()
        print 'resp_status:',r.status, r.reason
        #log(db, 'notify_one', 'conn res.status: %s  res.reason' % (r.status, r.reason))
        #print r
    except Exception as e:
        log(db, 'notify_one', 'ERROR: httplib.HTTPConnection(%s) -> %s' % (url_path, e))
        try:
            f = urllib.urlopen( shop.url + '/' + url_path)
            r = f.read()
            print 'resp_status:',r.status, r.reason, r.read()
        except Exception as e:
            log(db, 'notify_one', 'ERROR: urllib.urlopen(%s/%s) -> %s' % (host, url_path, e))
            pass
    conn_.close()
    return r
'''

def notify_one(db, note):
    #print note
    tries = note.tries or 0

    if tries > 6:
        # пусть сам магазин спрашивает если он не прочухался
        del db.shop_orders_notes[note.id]
        return
    if tries > 0:
        tmin = note.created_on
        dSec = 30 + 60*2**(tries - 1)
        dt_old = datetime.datetime.now() - datetime.timedelta(0, dSec )
        #print datetime.timedelta(0, 30 + dSec ), ' - ', dt_old
        if note.created_on > dt_old:
            #print 'till wail'
            return

    print 'note id:', note.id, 'tries:', tries
    # сюда пришло значит время пришло послать уведомление
    shop = shop_order = cmd = None
    if note.ref_id:
        # уведомление для счета
        shop_order = db.shop_orders[note.ref_id]
        shop = db.shops[shop_order.shop_id]
    elif note.cmd_id:
        # уведомление по выполненой команде
        cmd = db.shops_cmds[note.cmd_id]
        shop = db.shops[cmd.shop_id]

    if not(shop.url and len(shop.url)>5 and shop.note_url and len(shop.note_url)>1):
        # нету данных - удалим запись уведомления тогда
        del db.shop_orders_notes[note.id]
        return
    f = r = None

    r = notify_one_url(db, shop, shop_order, cmd)
    '''
    url_path = try_make_note_url2(db, shop, shop_order, cmd)
    if not url_path:
        # что-то не то с адресом - остави запись может адрес щас поменяем
        #del db.shop_orders_notes[note.id]
        #tries = 10
        #note.update_record(tries=tries)
        return

    r = None
    timeout = 2
    print 'try httplib.HTTPConnection(%s)' % shop.url
    try:
        #urllib.urlopen(url_resp)
        #f = urllib.urlopen(url_resp)
        #r = f.read()
        #log(db, 'notify_one', r)
        host = shop.url #'bitrent.in'
        #host = 'bitrent.in'
        if shop.url[0:7] == 'http://':
            host = shop.url[7:]
            conn_ = httplib.HTTPConnection(host, None, None, timeout)
        if shop.url[0:8] == 'https://':
            host = shop.url[8:]
            conn_ = httplib.HTTPSConnection(host, None, None, None, None, timeout)
        print host, conn_
    except Exception as e:
        log(db, 'notify_one', 'ERROR: httplib.HTTPConnectio(%s) -> %s' % (shop.url, e))
        return 'not connect - %s' % e
    print 'try  conn_.request(%s)' % url_path
    try:
        #url_path = '/index.php'
        #log(db, 'notify_one', 'url_path: %s' % url_path)
        #conn_.request('HEAD', url_path) # 'GET' не пашут почемуто?
        # HTTPS апшет, а HTTP нет
        # error - 301, removed - значит там вместо HTTP HTTPS и надо задавать адрес магазина https://bitrent.in
        conn_.request('HEAD', url_path)
        r = conn_.getresponse()
        print r.status, r.reason
        #print r
    except Exception as e:
        #log(db, 'notify_one', 'ERROR: urllib.urlopen(url_resp) -> %s' % e)
        pass
    conn_.close()
    '''
    tries = tries + 1
    note.update_record(tries=tries)
    return r

def notify(db):
    res = ''
    for note in db(db.shop_orders_notes).select():
        res = res + '%s<br>\n\n<br>' % notify_one(db, note)
    #db.commit()
    return res

#
# выплаты по отдельным счетам с автовыплатой
def bills_withdraw(db, curr, xcurr, cn):
    addrs = {}
    bills = {}
    amo_total = 0
    # возьмем резерв который для магазинов есть (за минусом моего резерва)
    bal_free = db_common.get_reserve(curr)
    # тут без учета что в магазинах есть - только свободные деньги db_common.get_shops_reserve( curr )
    #print '\n bills_withdraw, bal_free:', bal_free, curr.abbrev
    # берем заданные крипту и все балансы по ней
    for rec in db(db.bills_draws.curr_id == curr.id).select():
        amo = rnd_8(rec.amo) # за вычетом комиссии сети
        if amo <= 0: continue

        addr = rec.addr
        if not addr or len(addr) < 20:
            continue
        # тут может быть несколько выплат на один адрес - суммируем
        addrs[addr] = addrs.get(addr,0) + amo
        shop_order_ids = '%s' % rec.shop_order_id
        #print 'update', amo, rec.addr, shop_order_ids

        # накопим сумму для каждого счета отдельно
        bills[shop_order_ids] = bills.get(shop_order_ids, 0) + amo
        amo_total += amo
    #print addrs
    if len(addrs)==0: return # ничего не собрали
    #addrs_outs =

    bal_free = db_client.curr_free_bal(curr)
    print 'bal_free:', bal_free, ' amo_total to send:', amo_total
    if amo_total >= bal_free:
        log(db, 'bills_withdraw', 'ERROR: bal_free < amo_total - %s <' % (bal_free, amo_total))
        return
    # теперь надо выплату сделать разовую всем за раз
    # отлько таксу здесь повыше сделаем чтобы быстро перевелось
    #{ 'txid': res, 'tx_hex': tx_hex, 'txfee': transFEE }
    #print 'bills:', bills
    #print 'addrs', addrs
    #return
    #!!! вдруг база залочена - проверим это
    log(db,'bills_withdraw', 'try for addrs:%s' % addrs)
    res = crypto_client.send_to_many(db, curr, xcurr, addrs, float(xcurr.txfee or 0.0001), cn )
    if not res or 'txid' not in res:
        log(db, 'bills_withdraw', 'ERROR: crypto_client.send_to_many = %s' % res)
        return

    # удалим сразу
    db(db.bills_draws.curr_id == curr.id).delete()
    # деньги перевелись нужно зачесть это по счетам
    txid = res['txid']
    # а то вдруг база залочена - проверим это
    log(db,'bills_withdraw', 'txid:%s for addrs:%s' % (txid, addrs))
    # запоним а какой транзакции и сколько выплочено по этому счету
    for (bill_id, amo) in bills.iteritems():
        db.bills_draws_trans.insert(
                shop_order_id = bill_id,
                curr_id = curr.id,
                txid = txid,
                amo = amo,
                )

    #curr.update_record( balance - в serv_block_proc.run_once() один раз делается после блока
    # сохраним сразу данные!
    db.commit()


# сделать выплату если депозит магазинов больше withdraw_over или раз в сутки все
# withdraw_over - тогда не задаем
# запускается из serv_block_proc - когда найден новый блок
def withdraw(db, curr, xcurr, cn, withdraw_over=None):

    # сделать выплаты по отдельным счетам с автоплатежами
    bills_withdraw(db, curr, xcurr, cn)
    #print '\n WITHDRAW - [%s]' % curr.abbrev

    # если общий депозит всех магазинов достаточен то выплату им забабахаем
    txfee = xcurr.txfee
    if not withdraw_over:
        # если превышение = 0 то по умолчанию берем превышение по коммисии сети
        withdraw_over = txfee * 100
    elif curr.shops_deposit <= 0:
        return
    elif False and curr.shops_deposit < withdraw_over:
        return

    addrs = {}
    shops_bals = [] # нужно потом разделить по разным магазинам у кого былл один и тот же адрес
    amo_sum = 0
    # возьмем резерв который для магазинов есть (за минусом моего резерва)
    #print 'withdraw - ', db_common.get_reserve(curr)
    shops_reserve = db_common.get_shops_reserve(curr)
    # берем заданные крипту и все балансы по ней
    for bal_rec in db(db.shops_balances.curr_id == curr.id).select():
        #withdraw_over = bal_rec.withdraw_over or 0
        #if withdraw_over == 0:
        #    # если превышение = 0 то по умолчанию берем превышение по коммисии сети
        #    withdraw_over = txfee * 200
        # всем платим скопом! if bal_rec.bal < withdraw_over:
        #    continue

        ## без учета комиссии - нам и так больше сейчас должно приходить от покупателей
        amo = rnd_8(bal_rec.bal - 0*txfee) # за вычетом комиссии сети
        if amo < txfee * 5: continue
        #print ' witdraw bal-txfee = amo:', amo, curr.abbrev
        print ' witdraw bal:', amo, curr.abbrev

        # locket db
        shop = db.shops[bal_rec.shop_id]
        xwallet = db((db.shops_xwallets.shop_id == shop.id)
                        & (db.shops_xwallets.xcurr_id == xcurr.id)).select().first()
        if not xwallet: continue

        addr = xwallet.addr
        if not addr or len(addr) < 20:
            #print 'not valid addr:', addr
            continue

        valid = cn.validateaddress(addr)
        if not valid or 'isvalid' in valid and not valid['isvalid'] or 'ismine' in valid and valid['ismine']:
            #print 'not valid addr in withdraw:', addr, valid
            continue
        #print 'add amo to withdraw poll:', amo

        if amo_sum + amo > shops_reserve:
            # баланс крипты смотрим - если ее не хватило - прерываем накопление пула на выплаты
            log(db, 'withdraw', 'amo_sum %s > curr.balance %s [%s]' % (amo_sum + amo, shops_reserve, curr.abbrev))
            break
        shops_bals.append( [shop,  bal_rec.bal, addr] )
        addrs[addr] = addrs.get(addr, 0.0) + amo
        amo_sum += amo
    #print addrs
    if len(addrs)==0: return # ничего не собрали

    # теперь надо выплату сделать разовую всем за раз
    # отлько таксу здесь повыше сделаем чтобы быстро перевелось
    #{ 'txid': res, 'tx_hex': tx_hex, 'txfee': transFEE }

    #!!! вдруг база залочена - проверим это
    log(db,'withdraw', 'try for addrs:%s' % addrs)
    res = crypto_client.send_to_many(db, curr, xcurr, addrs, float(xcurr.txfee or 0.0001), cn )
    if not res or 'txid' not in res:
        log(db, 'withdraw', 'ERROR: crypto_client.send_to_many = %s' % res)
        return
    # деньги перевелись нужно зачесть это каждому
    txid = res['txid']
    # поидее надо запомнить что было перечисление
    log(db,'withdraw', 'txid:%s for addrs:%s' % (txid, addrs))

    ### запомним по каждому магазину теперь
    ti = cn.gettransaction(txid) # тут данные соттвествуют транзакции raw так как мы ее полностью сделали?
    trans_details = ti['details']
    for v in shops_bals:
        vout = 0
        for trans in trans_details:
            addr = trans[u'address']
            if addr == v[2]:
                break
            vout = vout + 1
        shop = v[0]
        amo = v[1]
        _, bal_new = insert_shop_trans_withdraw(db, shop, curr, amo, txfee, '{"txid": "%s", "vout": %s}' % (txid, vout))
        log(db, 'withdraw', 'shop: %s bal_new: %s txid: %s : %s' % (shop.url or shop.name, bal_new, txid, vout))

    # сохраним сразу данные!
    db.commit()
