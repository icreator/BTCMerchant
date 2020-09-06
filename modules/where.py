#!/usr/bin/env python
# coding: utf8
import datetime
import json

from gluon import current, URL, XML, A
T = current.T

import common
import crypto_client
import db_common

# addr - если не задан то не показываем проводки
# показываем только те что не зачлись еще и полные суммы заказа
def found_pay_ins_addr(T, db, addr, shop_order_id_in=None):
    pays =[]
    # все зачтенные за последний месяц
    # сначала выдадим все неоплоченные входы - они в стеке
    curr_in = xcurr_in = _ =None
    if shop_order_id_in:
        shop_order = db.shop_orders[shop_order_id_in]
        pp = shop_order.payed_soft + shop_order.payed_hard + shop_order.payed_true
        if pp == 0: pp ='0'
        pays.append({ T('Всего оплачено'):
                     '%s' % pp })
        #mess_pays = 'SOFT:%s, HARD:%s, TRUE:%s.' % \
        #    (shop_order.payed_soft, shop_order.payed_hard, shop_order.payed_true)
        #pays.append({'по статусам':  mess_pays})

    if addr:
        curr_in, xcurr_in, _ = db_common.get_currs_by_addr(db, addr)
        # если задан адрес то ищем проводки по нему
        for pay in db(
               (db.pay_ins.id == db.pay_ins_stack.ref_id)
               & (db.pay_ins.shop_order_addr_id == db.shop_order_addrs.id)
               & (db.shop_order_addrs.addr==addr)
               ).select(orderby=~db.pay_ins.created_on):
            xcurr = xcurr_in or db.xcurrs[pay.shop_order_addrs.xcurr_id]
            #if xcurr_in and xcurr_in.id != xcurr.id: continue
            curr_in = curr_in or db.currs[xcurr.curr_id]
        
            shop_order = shop_order or db.shop_orders[pay.shop_order_addrs.shop_order_id]
            shop = db.shops[shop_order.shop_id]
            curr_out = db.currs[shop_order.curr_id]
            curr_out = db.currs[shop_order.curr_id]
            ####################
            shop_name = db_common.get_shop_name(shop)
            status = pay.pay_ins.status
            #print '1pay.pay_ins.amo_out:', pay.pay_ins.amo_out
            amo_out = pay.pay_ins.amo_out
            if not amo_out or amo_out == 0: amo_out = '??'
            mess_in = '%s [%s] <- %s [%s] %s %s' % ( amo_out, curr_out.abbrev, pay.pay_ins.amount, curr_in.abbrev, status, pay.pay_ins.created_on)
            if pay.pay_ins.rate_order_id:
                rate_order = db.rate_orders[pay.pay_ins.rate_order_id]
                if rate_order:
                    mess_in = mess_in + T(' (курс по счету: %s)') % common.rnd_8(rate_order.volume_out / rate_order.volume_in)
            elif pay.pay_ins.amo_out and pay.pay_ins.amo_out != pay.pay_ins.amount:
                    mess_in = mess_in + ' (по текущему курсу: %s)' % common.rnd_8(pay.pay_ins.amo_out / pay.pay_ins.amount)
            pays.append({
                T('Вход'): mess_in,
                })
            #print '2pay.pay_ins.amo_out:', pay.pay_ins.amo_out
    
    return pays

def found_pay_ins(db, curr_in, xcurr_in, addr, shop=None, shop_order=None):
    pays =[]
    #print '\n',curr_in and curr_in.abbrev or 'curr_in=None', '\nSHOP:',shop.id, '\nshop_order:',shop_order.id
    # все зачтенные за последний месяц
    # сначала выдадим все неоплоченные входы - они в стеке
    used = {}
    privat = not addr or len(addr) < 4
    no_addr = privat or addr == "????"
    
    for pay in db( (not privat)
               & (db.pay_ins.id == db.pay_ins_stack.ref_id)
               & (db.pay_ins.shop_order_addr_id == db.shop_order_addrs.id)
               & (no_addr or db.shop_order_addrs.addr==addr)
#               & (xcurr_in and xcurr_in.id == db.shop_order_addrs.xcurr_id)
               ).select(orderby=~db.pay_ins.created_on):
        xcurr = db.xcurrs[pay.shop_order_addrs.xcurr_id]
        #if xcurr_in and xcurr_in.id != xcurr.id: continue
        curr_in = db.currs[xcurr.curr_id]
        #print
        
        shop_order = shop_order or db.shop_orders[pay.shop_order_addrs.shop_order_id]
        shop = shop or db.shops[shop_order.shop_id]
        shop_name = shop.name or shop.url or shop.mail
        if not privat:
            # показать подробно мне
            shop_name = '%s %s' % (shop_name or '', shop_order.order)
        status = pay.pay_ins.status
        pay_out_info = T('статус: ') + (status or T('в обработке'))
        used[pay.pay_ins.id]=True
        mess_in = '%s [%s] %s -> %s' % (pay.pay_ins.amount, curr_in.abbrev, pay.pay_ins.created_on, shop_name)
        pays.append({
            T('Вход'): mess_in,
            T('Выход'): pay_out_info,
            })
    # теперь все выплаченные - их в стеке уже нет и тут глубина - 40 дней
    # если без адреса то только 1 сутки
    expired = datetime.datetime.now() - datetime.timedelta(no_addr and 1 or 40, 0)
    for pay in db(
               (no_addr or db.shop_order_addrs.addr==addr)
               & (db.pay_ins.shop_order_addr_id == db.shop_order_addrs.id)
               & (db.pay_ins.created_on > expired)
               & (xcurr_in and xcurr_in.id == db.shop_order_addrs.xcurr_id)
               ).select(orderby=~db.pay_ins.created_on):
        if pay.pay_ins.id in used: continue
        #print pay
        xcurr = db.xcurrs[pay.shop_order_addrs.xcurr_id]
        #if xcurr_in and xcurr_in.id != xcurr.id: continue
        curr_in = db.currs[pay.shop_order_addrs.curr_id]

        shop_order = shop_order or db.shop_orders[pay.shop_order_addrs.shop_order_id]
        shop = shop or db.shops[shop_order.shop_id]
        curr_out = db.currs[shop_order.curr_id]
        dn_url = URL('order','show', args=[order.id])
        order_info = None
        if pay.pay_ins.order_id:
            order = db.orders[pay.pay_ins.order_id]
            order_info = T('№%s от %s, курс:%s') % (order.id, order.created_on, round(order.volume_out/order.volume_in,8))
        status = pay.pay_ins.status
        if status and status == 'returned':
            pay_out_info = T('Возвращен обратно')
        else:
            pay_out_info = T('НЕ ВЫПЛАЧЕН, статус: ') + (status or T('в обработке'))
        payout = rate = None
        if pay.pay_ins.payout_id:
            payout = db.pay_outs[pay.pay_ins.payout_id]
            if payout and payout.shoper_order_id:
                #shop_order = db.shop_orders[payout.ref]
                #shop = db.shops[shop_order.shop_id]
                shoper_order = db.shopers_orders[payout.shoper_order_id]
                #curr_out = db.currs[shoper_order.curr_id]
                shoper = db.shopers[shoper_order.shoper_id]
                shoper_shop = db((db.shoper_shops.shop_id == shop.id) & (db.shoper_shops.shoper_id == shoper.id)).select().first()
                #if shoper_shop.p2p and shop.name != 'WALLET':
                #    # если это выплата в магазин то переопределим ссылку
                #    dn_url = URL('to_shop','index')
                p_i = json.loads(payout.info)
                rate = round(payout.amount/payout.amo_in,8)
                amo_out = round(pay.pay_ins.amount * payout.amount/payout.amo_in, 2)
                #if not 'payment_id' in p_i: print payout.info, amo_out
                if 'payment_id' in p_i: pay_out_info = privat and  T('%s [%s] -%s%s %s') % ( amo_out, curr_out.abbrev, shoper_shop.tax, '%', payout.created_on ) or \
                    T('%s [%s] -%s%s %s %s %s') % (  amo_out, curr_out.abbrev, shoper_shop.tax, '%', p_i['payment_id'], 'invoice_id' in p_i and p_i['invoice_id'] or 'payee' in p_i and p_i['payee'], payout.created_on )
        elif pay.pay_ins.clients_tran_id:
            # это выплатата клиенту
            cl_tr = db.clients_trans[pay.pay_ins.clients_tran_id]
            clnt = db.clients[cl_tr.client_id]
            amo_out = cl_tr.amo_in
            rate = None
            pay_out_info = ''
            if cl_tr.curr_in_id and cl_tr.curr_in_id != curr_in.id:
                # была конвертация
                pay_out_info = pay_out_info + '%s [%s] ' % (amo_out, curr_out.abbrev)
                #rate = cl_tr.amo_in
            pay_out_info = pay_out_info + T('зачтено')
            if privat:
                dn_url = URL('to_shop','index', args=[cl_tr.client_id])
            else:
                pay_out_info = pay_out_info + T(' транзакция №%s - %s') % (cl_tr.id, cl_tr.desc)
                # to_shop/index/2?order=UUWZNTYIR&sum=0.02&curr_out=BTC
                vvv = {'order':shop_order.order, 'curr_out':curr_out.abbrev}
                if amo_rest: vvv['sum'] = amo_rest
                dn_url = URL('to_shop','index', args=[cl_tr.client_id],
                    vars=vvv)

        if not order_info and rate:
            order_info = T('текущий курс:%s') % round(rate,8)
        shop_name = shop.name
        if not privat:
            shop_name = '%s %s' % (shop.name, shop_order.order)
        shop_name = XML(A(shop_name, _href=dn_url))
        rec_vals = {
            T('Вход'): '%s [%s] %s' % (pay.pay_ins.amount, curr_in.abbrev, pay.pay_ins.created_on),
            T('Для'): shop_name,
            T('Заказ'): order_info,
            T('Выход'): pay_out_info,
            }
        if payout:
            if payout.amo_gift and payout.amo_gift > 0:
                rec_vals[T('Подарок')] = T('Вы получили дополнительно %s [%s]') % (payout.amo_gift, curr_out.abbrev)
            if payout.amo_partner and payout.amo_partner > 0:
                rec_vals[T('Партёрские')] = T('Вы получили дополнительно %s [%s]') % (payout.amo_partner, curr_out.abbrev)


        pays.append(rec_vals)
    
    return pays
