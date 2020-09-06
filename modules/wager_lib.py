# -*- coding: utf-8 -*-

from decimal import Decimal

import logging
logger = logging.getLogger("web2py.app.bs3b")
logger.setLevel(logging.ERROR) # DEBUG

# создадим список
# выплата всем кто оплатил на этот счет выигравщего условия
def make_pay_outs(db, cn, curr, xcurr, winned_bill_id, total_winned, pay_outs):
    
    # определим сколько кто заплатил по этому счету
    # только для этой валюты
    bill_addr = db((db.shop_order_addrs.shop_order_id == winned_bill_id)
        & (db.shop_order_addrs.xcurr_id == xcurr.id)).select().first()

    if not bill_addr:
        mess = 'bill_addr for bill.id %s [%s] not found' % (winned_bill_id, curr.abbrev)
        logger.error( mess )
        print 'make_pay_outs() ', mess
        return mess
    
    from crypto_client import sender_addr
    payers = {}
    # для всех входов что прошли
    for pay_in in db(db.pay_ins.shop_order_addr_id == bill_addr.id).select():
        #print pay_in
        if pay_in.status != 'TRUE':
            mess = "pay_in.status != 'TRUE' - break payout:"
            logger.debug( mess )
            print 'make_pay_outs() ', mess
            return mess
        
        txid = pay_in.txid
        vout = pay_in.vout
        mess = 'try get addrs from txid %s:%s' % (vout, txid)
        logger.debug( mess )
        print 'make_pay_outs() ', mess
        if not cn:
            mess = "not connected - break payout:"
            logger.error( mess )
            print 'make_pay_outs() ', mess
            return mess
        #try:
        inp = sender_addr(cn, txid)
        # тут получим список входов - возьмем самый максимальный вход и его адрес

        #except Exception as e:
        #    print 'ERROR sender_addrs: %s' % e
        #    return
        mess = "input addr: %s" % inp
        logger.debug( mess )
        print 'make_pay_outs() ', mess

        if type(inp) == type({}):
            mess =  'ERROR: type(inps) == type({}) %s' % inp
            logger.error( mess )
            print 'make_pay_outs() ', mess
            return mess
        
        payers[inp] = payers.get(inp, 0) + pay_in.amount

    # сложим платежи с уже тем списком что есть
    print 'PAYERS:', payers

    winned_bill = db.shop_orders[winned_bill_id]
    for payer, payed in payers.iteritems():
        pay_outs[payer] = pay_outs.get(payer, 0) + total_winned/winned_bill.payed_true * payed

# solve_one(db, curr, xcurr, conn, wager_stack)
def solve_one(db, curr, xcurr, conn, stck):
    wager = db.wagers[ stck.ref_id ]
    if not wager:
        del db.wagers_stack[ stck.id ]
        mess = 'wager not found'
        logger.error( mess )
        print 'solve_one() ', mess
        return

    if wager.status != 'END':
        mess = "status %s != 'END'" % wager.status
        logger.error( mess )
        print 'solve_one() ', mess
        return
    
    if wager.curr_id != curr.id:
        mess = 'wager.curr_id != curr.id'
        logger.error( mess )
        print 'solve_one() ', mess
        return
    
    # если еще не все прошли платежи
    total = Decimal(0)
    total_in_progress = Decimal(0)
    for bill_id in wager.bill_ids:
        bill = db.shop_orders[ bill_id ]
        if not bill: continue
        
        total_in_progress += bill.payed_soft + bill.payed_hard
        total += bill.payed_true
    
    # еще есть не прошедшие все подтверждение
    if total_in_progress:
        mess = 'total_in_progress: %s' % total_in_progress
        logger.debug( mess )
        print 'solve_one() ', mess
        return
    
    wins = len(wager.winner_ids)
    if wins == 0:
        del db.wagers_stack[ stck.id ]
        mess = 'wins == 0'
        logger.error( mess )
        print 'solve_one() ', mess
        return

    # тут непонятно сколько коммисия будет так как размер непонятен
    ## total = total - xcurr.txfee
    # учтем нашу мзду и мзду создателя
    total_lc = total * wager.keep
    #  и мзду создателя
    maker_fee = total_lc * wager.maker_fee
    total_winned = (total_lc - maker_fee)/Decimal(wins)
    print 'total_lc, maker_fee, total_winned', total_lc, maker_fee, total_winned
    mess = 'total %s, wins: %s, total_winned: %s' % (total, wins, total_winned )
    logger.debug( mess )
    print 'solve_one() ', mess
    
    pay_outs = {}
    for winned_bill_id in wager.winner_ids:
        mess = 'winned_bill_id: %s' % winned_bill_id
        logger.debug( mess )
        print 'solve_one() ', mess
        err = make_pay_outs(db, conn, curr, xcurr, winned_bill_id, total_winned, pay_outs)
        if err: return err
    
    del db.wagers_stack[ stck.id ]
    wager.update_record(status = 'END')
    
    logger.error('pay_outs: %s' % pay_outs)
    mess = 'pay_outs fo WINNERS: %s' % pay_outs
    logger.debug( mess )
    print 'solve_one() ', mess
    for addr, amo in pay_outs.iteritems():
        db.bills_draws.insert(
            shop_order_id = winned_bill_id,
            curr_id = curr.id,
            addr = addr,
            amo = round(float(amo),8),
            )
    
    # теперь для создателя спора выпоату добавим
    db.bills_draws.insert(
            shop_order_id = winned_bill_id,
            curr_id = curr.id,
            addr = wager.maker_addr,
            amo = maker_fee,
            )
    
    
    # обновим баланс сохоаненых запасов
    xw = db((db.shops_balances.shop_id == wager.shop_id)
            & (db.shops_balances.curr_id == curr.id)).select().first()
    if not xw:
        # поидее этого не может быть - 0й баланм уйет в минус
        id = db.shops_balances.insert(
                shop_id = shop.id,
                curr_id = curr.id,
                bal = 0,
                kept = 0.0,
                )
        xw = db.shops_balances[id]

    xw.update_record(kept = xw.kept - total_lc)

    mess = 'inserted in db.bills_draws'
    logger.debug( mess )
    print 'solve_one() ', mess

# это вызываем из сервера обработки ставок
# парамет на входе - чтобы не могли вызвать из броузера
def solve(db, curr, xcurr, conn):
    #return
    wagers_stack = db(db.wagers_stack.curr_id == curr.id).select()
    for stck in wagers_stack:
        solve_one(db, curr, xcurr, conn, stck)
