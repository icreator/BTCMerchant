#!/usr/bin/env python
# coding: utf8
#from gluon import *

import shops_lib

# берем адреса на возврат или выплату из таблицы и
# формируем send_many
#  комиссию тут не учитываем - не вычитаем ! - при создании записей на возврат это надо делать??
def return_refused(db, curr, xcurr, conn, curr_block, table):
    # возвраты - вышлем за раз все по даной крипте
    addrs = {}
    ids = []
    vol = 0.0
    for r in db(table.xcurr_id == xcurr.id).select():
        if curr_block - xcurr.conf_hard - 2 < r.in_block: continue # только зрелые назад возвернем
        # тут надо еще проверить - а не исчезла ли эта проводка - мож она доубле спенд былда или в блоке двойном
        if r.txid and len(r.txid)>20 and not crypto_client.trans_exist(conn, r.txid):
            ####  тут отдельные выходы не проверяем на малость их - только сумму -- r.amount < xcurr.txfee*3:
            # это не выплата для тестового_магазина - там в записи адрес уже стоит
            # и такой транзакции в сети  нету - то ли доубле-спенд то ли не подтвердилась потом
            #  - ее удалим из базы и всё
            del table[r.id]
            continue
        # такой платеж возвращаем
        sender_addr = r.addr
        if not sender_addr:
            sender_addr = crypto_client.sender_addr(conn, r.txid)
            if not sender_addr: continue
            r.update_record( addr = sender_addr)
        #amo = round(float (r.amount - xcurr.txfee * 2), 8)
        amo = common.rnd_8(r.amount)
        print 'RETURN:',curr.abbrev, amo, sender_addr
        if amo >0: addrs[sender_addr] = amo
        vol += amo
        ids.append( r.id )
        #txid = conn.sendtoaddress(sender_addr, amo )
        #print txid

    if len(ids)==0: return
    # собрали все кому надо вернуть
    if vol < float(xcurr.txfee) * 10:
        print 'serv_block_prov: refused vol so small', vol, '<',float(xcurr.txfee) * 10
    else:
        # если размер выплат больше чем комиссия
        # то попытаемся их выплатить
        res = crypto_client.send_to_many(db, curr, xcurr, addrs)
        log(db, 'return_refused', 'RETURN res: %s' % res)
        txid = res and res.get('txid')
        if txid:
            # если выплата прошла то удалим записи
            for id in ids:
                del table[id]
            db.commit()
        return txid
    return

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
    return Decimal(amo_keep)

def insert_shop_trans_withdraw(db, shop, curr, amo, txfee, desc):
    # изменим баланс валют на счетах клиента
    bal = shops_lib.update_bal(db, shop, curr, -amo)
    shops_trans_id = db.shops_draws.insert(
        shop_id = shop.id,
        curr_id = curr.id,
        amo = amo - txfee,
        desc_ = desc,
        )
    print '%s[%s] withdrawed to SHOP %s' % (amo, curr.abbrev, shop.name or shop.url or shop.id)
    return shops_trans_id, bal

#
# выплаты по отдельным счетам с автовыплатой
def bills_withdraw(db, curr, xcurr, cn):
    addrs = {}
    bills = {}
    # возьмем резерв который для магазинов есть (за минусом моего резерва)
    bal_free = db_common.get_reserve(curr)
    # тут без учета что в магазинах есть - только свободные деньги db_common.get_shops_reserve( curr )
    print '\n bills_withdraw, bal_free:', bal_free, curr.abbrev
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
        print 'update', amo, rec.addr, shop_order_ids

        # накопим сумму для каждого счета отдельно
        bills[shop_order_ids] = bills.get(shop_order_ids, 0) + amo
    #print addrs
    if len(addrs)==0: return # ничего не собрали
    #addrs_outs = 

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
    if withdraw_over and withdraw_over == 0:
        # если превышение = 0 то по умолчанию берем превышение по коммисии сети
        withdraw_over = txfee * 5000
    if withdraw_over and curr.shops_deposit < withdraw_over: return

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
        amo = rnd_8(bal_rec.bal - txfee) # за вычетом комиссии сети
        if amo <= 0: continue
        print ' witdraw bal-txfee = amo:', amo, curr.abbrev

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
            print 'not valid addr in withdraw:', addr, valid
            continue
        #print 'add amo to withdraw poll:', amo

        if amo_sum + amo > shops_reserve:
            # баланс крипты смотрим - если ее не хватило - прерываем накопление пула на выплаты
            log(db, 'withdraw', 'amo_sum %s > curr.balance %s [%s]' % (amo_sum + amo, shops_reserve, curr.abbrev))
            break
        shops_bals.append( [shop,  bal_rec.bal, addr] )
        addrs[addr] = addrs.get(addr, 0.0) + amo
        amo_sum = amo_sum + amo
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
        print 'bal new:', bal_new

    # сохраним сразу данные!
    db.commit()
