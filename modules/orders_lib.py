#!/usr/bin/env python
# coding: utf8

# TODO
# при релимите - ссделать подпрограмку и испытывать через тулс на мелких и больших суммах
#
## при определнии адреса отправителя - если нет связи с кошельком..
## создавать 1 раз и потом оттуда брать а не каждый раз поновой искать

STARTUP_SHOP_ID = 6 # мой стартап - его статы меняем

UNUSED_STATUSES = [ 'CLOSED', 'EXPIRED', 'INVALID' ]


#from gluon import *
import datetime
import time
from decimal import Decimal # тут преимущественно все в Decimal

import shops_lib
from common import rnd_8
import db_common
import rates_lib
import crypto_client
from gluon.shell import exec_environment
try:
    import applications.test.modules.common
    TEST_SHOP_ID = applications.test.modules.common.SHOP_ID
    test_DB = exec_environment('applications/test/models/db.py')
except:
    try:
        import applications.test_shop.modules.common
        TEST_SHOP_ID = applications.test_shop.modules.common.SHOP_ID
        test_DB = exec_environment('applications/test_shop/models/db.py')
    except:
        TEST_SHOP_ID = test_DB = None


def log(db, l2, mess='>'):
    m = 'orders_lib'
    print m, l2, mess
    db.logs.insert(label123456789=m, label1234567890=l2, mess='%s' % mess)
def log_commit(db, l2, mess='>'):
    log(db, l2, mess)
    db.commit()

# проверка входящих параметров для запросов - 3 варианта входа
# /[shop_order_id]
# /[shop_id]/[order_id]
# /[shop_id]?order=[order_id]
def check_args(db, request):
    err = shop = order_id = shop_order = None
    if not request.args or len(request.args)==0:
        err = { "error": "args is empty" }
        return err, shop, order_id, shop_order
    if len(request.args)==1 and (not request.vars or len(request.vars)==0 or not request.vars.get('order')):
        # значит тут только номер заказа в нашем сервисе - без доп параметров
        # этого достаточно
        id = request.args[0]
        ids = str(id).split('.')
        #print ids, ids[0].isdigit()
        if ids[0].isdigit():
            #isinstance( shop_order_id, int ):
            # возьмем только целую часть
            id = int(ids[0])
            shop_order = db.shop_orders[id]
            if not shop_order:
                err = { 'error': 'bill_id is empty'}
                time.sleep(2)
                return err, shop, order_id, shop_order

            if shop_order.secr:
                # счет секретный - выдавать его только по секретному коду (хэш),
                # который в дробной части добавлен
                # возьмем дробную часть
                secr1 = len(ids) > 1 and ids[1]
                if secr1 != shop_order.secr:
                    # пусть для bill/SHOW  - это создать новый счет
                    # order_id = shop_order.order_id
                    shop_order = None
                    err = { 'error': 'bill is secret'}
                    # добавим задержку на неудачный запрос
                    time.sleep(10)
            else:
                # был доступ без секретного ключа
                # - введем задержку на перебор
                # чтобы народ быстро не перебирал счета по АПИ
                time.sleep(1)

            # там статус ИНВАЛИД выдаст if not shop_order:
            #    err = { 'error': 'bill not exist'}
            #    return err, shop, order_id, shop_order
        else:
            # похоже тут вмето номера магазина его адрес кошелька - значит нужен ЗАКАЗ еще
            err = { 'error': 'bill_id is empty'}
            time.sleep(2)

        return err, shop, order_id, shop_order

    shop_id = request.args[0]
    shop, shop_id = shops_lib.is_simple_shop(db, request.vars, shop_id)
    if not shop:
        err = { "error": "shop [%s] not found" % request.args[0] }
        return err, shop, order_id, shop_order

    if request.args and len(request.args)>1:
        order_id = request.args[1]
    elif request.vars and len(request.vars)>0:
        order_id = request.vars.get('order')

    if not order_id:
        err = { "error": "field [order] not found" }
        return err, shop, order_id, shop_order

    shop_order = db_common.get_shop_order(db, shop, order_id)
    if not shop_order:
        err = { "error": "[order_id] for [shop_id]  not found" }
    return err, shop, order_id, shop_order

#################################################

# эта функция вызвается из cryptoPay когда там меняется заказ - вместо нотификации
# и передается сумма заказа
# import applications.test.modules.crypto_client.note(order_id, order_payed)
def note_test(db, so, shop):
    if not test_DB: return
    
    to_payout = Decimal(0)
    #print test_DB.db().select(test_DB.db.orders.ALL)
    #print test_DB.db(test_DB.db.orders).select()
    test_order = test_DB.db(test_DB.db.orders.order_id == so.order_id).select().first()
    if not test_order: return # это я сам вручную сдедал заказ а не с сайта
    #test_order = test_DB.db.orders[so.order_id]
    price = so.price
    if price:
        # это заказ с окончанием - тогда смотрим по статусу
        if so.status in ['HARD', 'CLOSED']:
            if test_order.payouted < price:
                to_payout = price - test_order.payouted
    else:
        # если продолженные заказ то берем по ХАПД и разницу с выплочено уже
        to_payout = so.payed_hard + so.payed_true - test_order.payouted

    if not to_payout: return

    print 'TO PAYOUT:',to_payout, 'for:',test_order.id

    curr_out = db.currs[so.curr_id] # тут валюта в котрой заказ
    xcurr_out = db(db.xcurrs.curr_id==curr_out.id).select().first()
    if not xcurr_out: return
    #amo_tx = round(float(to_payout - 2*xcurr_out.txfee),8)
    # уже лимитом add_limit вычли из них стоимость транзакции
    amo_tx = rnd_8(to_payout)
    pay_ins_return_id = None
    if amo_tx > 0:
        pay_ins_return_id = db.pay_ins_return.insert(
             xcurr_id = xcurr_out.id, # тут валюта в котрой заказ
             addr = test_order.addr,
             in_block = 1,
             # неуказываем вообще так как там иначе будет поиск
             # транзакции по txid - вдруг она отвергнута сетью ---- txid='', vout = 0,
             amount = amo_tx,
             )
    shops_lib.insert_shop_trans_withdraw(db, shop, curr_out, to_payout, 'withdraw to TEST order:%s' % test_order.id)
    # не надо, так как мы тут не выводим крипту - только БД правим db.commit()
    # запомним тут что вывели
    #applications.test.modules.common.note(db, shop_order)
    test_order.update_record(payouted = test_order.payouted + to_payout, payout_res = 'withdraw pay_ins_return_id:%s' % pay_ins_return_id)
    # сохраним тут так как кам везде эта запись одна идет
    test_DB.db.commit()


def del_note(db, shop_order):
    if not shop_order: return
    #print 'del NOTE for shop_order.id:', shop_order.id
    try:
        db(db.shop_orders_notes.ref_id == shop_order.id).delete()
    except Exception as e:
        log(db, 'del_note', 'ERROR shop_order %s' % e)


def make_note(db, shop_order, shop, curr, xcurr):
    print 'make NOTE for shop_order.id:', shop_order.id
    if shop_order.shop_id == TEST_SHOP_ID:
        if not shop_order.price or shop_order.status in ['HARD', 'TRUE']:
            # если статус норм то выплату сделаем
            # причем там проверка на выплаченные уже суммы - поидее 2 раза не выплотится
            note_test(db, shop_order, shop)
        return
    elif shop_order.shop_id == STARTUP_SHOP_ID:
        founder = db(db.startup.passport==shop_order.order_id).select().first()
        if founder:
            founder.update_record(founded = shop_order.payed_hard + shop_order.payed_true)
        else:
            log(db,'make_note', ' STARTUP passport [%s] not found!' % shop_order.order_id)
        return
    # import applications.test.modules.crypto_client.note(order_id, order_payed)
    note_on = shop_order.note_on
    if note_on:
        note_on = note_on.upper()
        if note_on == 'HARD' and shop_order.status == 'SOFT': return
        elif note_on == 'CLOSED' or note_on == 'TRUE':
            if shop_order.status == 'SOFT' or shop_order.status == 'HARD': return
    shop_orders_note = db(db.shop_orders_notes.ref_id == shop_order.id).select().first()
    if shop_orders_note:
        log(db, 'make_note', 'update NOTE[%s] trues = 0 ' % shop_orders_note.id)
        shop_orders_note.update_record( tries = 0 )
    else:
        id_ = db.shop_orders_notes.insert(ref_id = shop_order.id)
        log(db, 'make_note', 'insert NOTE[%s] for shop_order.id = %s' % (id_, shop_order.id))

def set_status(db, shop_order, status, note=None, shop=None, curr=None, xcurr=None):
    print 'new status %s for shop_order.id: %s' % ( shop_order.id, status)
    shop_order.update_record(status = status)
    if note:
        print 'make_note'
        make_note(db, shop_order, shop, curr, xcurr)


# сюда приходит если поменялся статус у входа
# тут присваивается курс обмена если подтв достаточено
# обновим суммы у заказа - уменьшим сумму старого статуса и увеличим сумму нового
def update_payed(db, curr, xcurr, pay_in, old_status, new_status, conf, shop_order, shop_order_addr):
    print 'pay in: OLD STATUS:', old_status, '-> new status:', new_status, ' confs:', conf
    # тут надо решить  моожно ли такой платеж с таким статусом брать в расчет
    # оплаты счета - ведь если подтверждений меньше 1 и курс не 1 то когда он придет
    # может курс поменяться сильно
    amo_out = pay_in.amo_out # тут кол-во сковертированное в крипте оплаты заказа
    if not amo_out or amo_out == 0:
        # если мы незнаем курса то и ничего сделать не сможем
        # поэтому менять статус не будем
        # так как если статус станет ТРУЕ а курса нет то фигня получится
        print 'amo_out == 0'
        return

    shop_order_addr = shop_order_addr or db.shop_order_addrs[pay_in.shop_order_addr_id]
    shop_order = shop_order or db.shop_orders[shop_order_addr.shop_order_id]
    #shop = db.shops[shop_order.shop_id]

    # статус меняем только когда есть обменный курс!
    pay_in.update_record(status = new_status, status_dt = datetime.datetime.now())

    # теперь со статусом заказа разберемся
    order_status = shop_order.status
    if order_status in UNUSED_STATUSES:
        if new_status == 'TRUE':
            # такой вход подлежит возврату
            log(db, 'update_payed', 'order status [%s] in UNUSED and new TRUE pay_in %s -> return_pay_ins_one'
                % (order_status,pay_in.id))
            return_pay_ins_one(db, xcurr, pay_in, pay_in.amount, 'RETURNED') # вернем все
        # больше ничего не делваем - выход
        return

    if old_status == 'HARD':
        shop_order.update_record( payed_hard = shop_order.payed_hard - amo_out )
    elif old_status == 'SOFT':
        shop_order.update_record( payed_soft = shop_order.payed_soft - amo_out )
        #if shop_order.payed_soft <0: shop_order.payed_soft = 0

    if order_status == 'NEW':
        # если заказ продолжиельный то тут ему статус сменим
        shop_order.update_record(status = 'FILL')
        #set_status(db, shop_order, 'FILL')

    price = shop_order.price
    is_closed_order = price and price > 0 # это заказ который можно закрыть?
    if new_status == 'SOFT':
        shop_order.update_record( payed_soft = shop_order.payed_soft + amo_out )
    elif new_status == 'HARD':
        shop_order.update_record( payed_hard = shop_order.payed_hard + amo_out )
    elif new_status == 'TRUE':
        if not is_closed_order:
            # это продолженный заказ - выдадим пользователю вход
            shop_order.update_record( payed_true = shop_order.payed_true + amo_out )
            shop=db.shops[shop_order.shop_id]
            if shop_order.not_convert:
                # конвертировать не надо
                amo_shop = pay_in.amount
                curr_shop = curr
            else:
                amo_shop = amo_out
                curr_shop = db.currs[shop_order.curr_id]
            shops_lib.insert_shop_trans_order(db, shop_order, amo_shop, shop, curr_shop, '{ "type":"fill", "txid": %s, "vout": %s }' % (pay_in.txid, pay_in.vout), curr, pay_in.amount)
            make_note(db, shop_order, shop, curr, xcurr) # тут сразу уведомление делаем об этом заказе
            return

        # сюда придет только с ценой заказ - закрываемый
        # добавим погрешность на изменение курса
        # причем тут надо цену снизить чуток - так как она была увеличина нами при оплате заказа
        # тут amo_out уже с добавкой ЛИМИТ на курс (orders_lib.add_limit)
        price_limit1 = rates_lib.add_limit( price, xcurr.txfee, -1, -1)
        price_limit2 = rates_lib.add_limit( price, xcurr.txfee, 0, 3) # возврат с лимитом
        print 'price:', price, 'price_limit1 - for update:', price_limit1, 'price_limit2 - for return:', price_limit2
        #print 'shop_order.payed_true + amo_out:', shop_order.payed_true + amo_out
        if price_limit1 < shop_order.payed_true + amo_out:
            # на закрытие уже пришло больше чем надо
            # пересчитаем приход этого входа до целого числа ЦЕНЫ
            # поидее нужно и у входа апдейт сделать для amo_out
            amo_out = price - shop_order.payed_true
            print 'price - shop_order.payed_true:', price - shop_order.payed_true
            if amo_out > 0:
                amo_diff = pay_in.amo_out - amo_out
                if amo_diff > 0:
                    # определим часть возврата по курсу
                    amo_ret = rnd_8(pay_in.amount * amo_diff / pay_in.amo_out)
                    if amo_ret > float(xcurr.txfee) * 2.0:
                        log(db, 'update_payed', 'RETURN amo_ret: %s = %s * %s / %s' %
                            (amo_ret, pay_in.amount, amo_diff, pay_in.amo_out))
                        return_pay_ins_one(db, xcurr, pay_in, amo_ret) # вернем часть оставшуюся
        # теперь сложим
        shop_order.update_record( payed_true = shop_order.payed_true + amo_out )

    if not is_closed_order:
        # все прочие статусы входов для незакрываемыз заказов - выход
        # так как они не дают клиенту ничего и заказ не меняют
        # только пошлем уведомление что суммы статусов поменялись
        shop=db.shops[shop_order.shop_id]
        make_note(db, shop_order, shop, curr, xcurr) # тут сразу уведомление делаем об этом заказе
        return
    # теперь проверим изменение статуса заказа
    # сюда прийдет только действующий закрываемый заказ c
    if price > shop_order.payed_true + shop_order.payed_hard + shop_order.payed_soft:
        # суммы всех платжей недостаточно для смены статуса - выход
        return

    # сюда пришло значит цена закза оплачена - вопрос только насколько подтверждено это
    note = True
    print price,'<=', shop_order.payed_true + shop_order.payed_hard , 'status:', order_status
    if price <= shop_order.payed_true and order_status != 'CLOSED':
        shop=db.shops[shop_order.shop_id]
        set_status(db, shop_order, 'CLOSED', note, shop, curr, xcurr) # с уведомлением
        # тут же надо его выкинуть из стека по протуханию
        db(db.shop_orders_stack.ref_id==shop_order.id).delete()
        # заказ оплачен полностью - он передается магазину
        shop=db.shops[shop_order.shop_id]
        if shop_order.not_convert:
            # конвертировать не надо
            # тут надо по всем входам счета прогнать и для всех валют создать свои транзакции
            for r in db(
                (shop_order.id == db.shop_order_addrs.shop_order_id)
                & (db.shop_order_addrs.id == db.pay_ins.shop_order_addr_id)
                & (db.shop_order_addrs.xcurr_id == db.xcurrs.id)
                & (db.xcurrs.curr_id == db.currs.id)
                        ).select():
                amo_shop = r.pay_ins.amount - (r.pay_ins.amo_ret or Decimal(0))
                curr_shop = r.currs
                shops_lib.insert_shop_trans_order(db, shop_order, amo_shop, shop, curr_shop, '{  "type":"closing", "order": %s, "shop_order": %s, "txid": %s, "vout": %s, "amount": %s, "amo_ret": %s }' % (shop_order.order_id, shop_order.id, r.pay_ins.txid, r.pay_ins.vout, r.pay_ins.amount, r.pay_ins.amo_ret), curr, pay_in.amount)
        else:
            amo_shop = price
            curr_shop = db.currs[shop_order.curr_id]
            shops_lib.insert_shop_trans_order(db, shop_order, amo_shop, shop, curr_shop, '{  "type":"closing", "order": %s, "shop_order": %s }' % (shop_order.order_id, shop_order.id), curr, pay_in.amount)
    elif price <= shop_order.payed_true + shop_order.payed_hard and order_status != 'HARD':
        shop=db.shops[shop_order.shop_id]
        set_status(db, shop_order, 'HARD', note, shop, curr, xcurr)
    elif order_status != 'SOFT':
        # статус был или 'NEW' или 'FILL'
        shop=db.shops[shop_order.shop_id]
        set_status(db, shop_order, 'SOFT', note, shop, curr, xcurr)
    pass

# здесь если заказ продолженный то проводки с ТРУЕ зачисляем на счет магазина
# и наче ничего не делаем - а делаем целиком по заказу
# сюда может прийти статус новый только HARD + TRUE --- SOFT поидее сам должен гдето присвиваться - по умоляанию при создании
# здесь только меняем статусы у самого входа и запоминаем заказ на проверку
def inputs_update(db, curr_block, curr, xcurr, conn):
    pay_ins_st = db(db.pay_ins_stack.xcurr_id==xcurr.id).select()
    if len(pay_ins_st)==0: return 'pay_ins enpty'
    # все приходы в стеке - пока они там значит они не ДОНЕ и не начислены еще магазину
    conf_true = xcurr.conf_true == None and 6 or xcurr.conf_true
    conf_hard = xcurr.conf_hard == None and 3 or xcurr.conf_hard
    conf_soft = xcurr.conf_soft == None and 1 or xcurr.conf_soft
    #print 'inputs_update [%s]%s' % (curr.id, curr.abbrev), conf_soft, conf_hard, conf_true
    rates = rates_lib.get_best_rates(db, curr) # загодя возьмем курсы обмена для этой крипты
    #print rates
    #print conf_soft, xcurr
    # у каждого адреса - может быть много проводок - поэтому потом по адресам смотрим
    for r in pay_ins_st:
        #print r
        pay_in = db.pay_ins[r.ref_id]
        pay_old_status = pay_in.status
        pay_old_status = len(pay_old_status or '')>0 and pay_old_status or '-' # пустые и с длинною 0 - как пустые
        conf = curr_block - pay_in.in_block + 1
        #print 'OLD STATUS:', pay_old_status, 'PAY_IN:', pay_in.amount, pay_in.amo_out, '\nconf:', conf

        shop_order_addr = db.shop_order_addrs[pay_in.shop_order_addr_id]
        shop_order = db.shop_orders[shop_order_addr.shop_order_id]
        # проверим - есть ли связь с кошельком сначала а потом проверим транзакцию
        bbb = conn.getblockcount()
        if not crypto_client.trans_exist(conn, pay_in.txid):
            # а есть ли ввобще такая проводка? мож она была в двойной цепочке блоков и исчезла
            new_status = 'INVALID'
            pay_in.amo_out = -1 ##  зададим курс иначе в update_payed статус не поменяется
            del db.pay_ins_stack[r.id]
            update_payed(db, curr, xcurr, pay_in, pay_old_status, new_status, conf, shop_order, shop_order_addr)
            continue

        # определим сразу тут курс!!
        amo_out = pay_in.amo_out
        #print 'AMO_OUT: ',amo_out
        if not amo_out or amo_out == 0:
            # если курс еще не вычислен - попробуем его задать
            curr_out = db.currs[shop_order.curr_id]
            #print 'curr -> curr_out', curr.abbrev, curr_out.abbrev
            if curr.id == curr_out.id:
                # это без обмена
                amo_out = pay_in.amount
                pay_in.update_record(amo_out = amo_out)
            elif conf > 0 and shop_order.status not in UNUSED_STATUSES:
                # если подтверждения уже есть и счет еще не протух то ищем обменный курс
                #print 'orders_lib: try rates_lib.get_amo_out'
                # изменим величину входа -
                # уменьшим погрешности на колебания курса - тут минусуем
                # берем именно крипту входа и ее txfee
                # тут уже с добавкой пришла крипта поэтому:
                # -если заказ на курс жив то все без изменений - там лимит уже забит
                # -если заказ на курс просрочен то тут получится завышенное кол-во на входе
                # поэтому нужно уменьшитть

                amo_out, rate_order, rate_ = rates_lib.get_amo_out(db, rates, shop_order_addr, curr_out,
                                                           pay_in.amount, pay_in.created_on)
                # если нет курса... то будет 0
                if not amo_out:
                    # если нет курса то не надо его обрабатывать на таксу и тд
                    pass
                else:
                    if rate_order:
                        # если по заказу на курс то ничего не делаем - там уже все учтено
                        pass
                    else:
                        # если по текущему курсу то вычтем лиимит на колебания курса
                        ##amo_out = rate_ * rates_lib.add_limit( pay_in.amount, xcurr.txfee, -0.8, -0.8)
                        ## НЕТ без уменьшения курса - просто сдачу потом вернем
                        amo_out = rate_ * float(pay_in.amount)
                        #print 'not rate_order -> amo_in limited -0.8, -0.8'
                    #print 'amo_out, rate_, rate_order', amo_out, rate_, rate_order
                    amo_out = Decimal(amo_out)
                    price = shop_order.price
                    if price:
                        # если задана цена то погрешность курса нивелируем - так как было заплочено больше на limit+1+1
                        # теперь надо глянуть погрешность между ценою, остатком для доплаты и данным входом
                        # если разница небольшая то принять погрешность
                        all_payed = shop_order.payed_true + shop_order.payed_hard + shop_order.payed_soft
                        print 'amo_out:', amo_out, 'all_payed:', all_payed
                        all_payed_full = all_payed + amo_out
                        ## тут и так уже погрешность добавлена (выше) к величине входов
                        print 'all_payed_full:', all_payed_full
                        diff_ = all_payed_full - price
                        accur_ = abs(float(diff_ / price))
                        print 'accur_:', accur_
                        if accur_ < 0.01:
                            # погрешность очень маленькая - простим ее
                            amo_out = price - all_payed
                            print 'accurated amo_out:', amo_out

                    # если курс нашелся то обновим amo_out
                    pay_in.update_record(
                        rate_order_id = rate_order and rate_order.id or None,
                        amo_out = amo_out)
                    print 'update amo_out:', amo_out, 'rate_order:', rate_order


        if conf >= conf_true:
            new_status = 'TRUE'
            #if conf >= conf_true + 2:
            if conf >= conf_true + 3 * conf_true * (1 + pay_in.tryed):
                pay_in.update_record( tryed = pay_in.tryed + 1)
                log(db, 'inputs_update', 'conf >= conf_true *10 **TRY: %s** - [%s]%s %s'
                    % (pay_in.tryed, curr.abbrev, pay_in.amount, pay_in.txid))

            if not amo_out:
                ###
                ### ВНИМАНИЕ !!!! кол-во подтверждений может быть и намного больше - если
                ### если сервис подвис или курс неизвестен - поэтому нельзя возвращать сразу обратно
                ###
                if not shop_order.price:
                    # Эта запись подвисла - видимо курса нет - надо ее вернуть
                    # такой вход подлежит возврату
                    ## !!!!!!!!!!!!!!!! это платеж от пула - ннельзя возвращать!
                    ##del db.pay_ins_stack[r.id]
                    ##return_pay_ins_one(db, xcurr, pay_in, pay_in.amount, 'RETURNED') # вернем все
                    if pay_in.tryed < 8:
                        continue
                    else:
                        # на возврат платежа
                        log(db, 'inputs_update', 'DEL from pay_in_STACK pay_ins.id: %s and RETURN' % r.id)
                        del db.pay_ins_stack[r.id]
                        return_pay_ins_one(db, xcurr, pay_in, pay_in.amount, 'RETURNED') # вернем все
                        if not amo_out:
                            # запомним что нет курса и поэтому удаляем
                            log(db,'inputs_update', 'becouse not RATE for %s -> %s' % (curr.abbrev, curr_out.abbrev))
                        continue
                elif shop_order.status in UNUSED_STATUSES:
                    # на возврат платежа
                    log(db, 'inputs_update', 'DEL from pay_in_STACK pay_ins.id: %s and RETURN' % r.id)
                    del db.pay_ins_stack[r.id]
                    return_pay_ins_one(db, xcurr, pay_in, pay_in.amount, 'RETURNED') # вернем все
                    continue
                else:
                    continue

            del db.pay_ins_stack[r.id]
            update_payed(db, curr, xcurr, pay_in, pay_old_status, new_status, conf, shop_order, shop_order_addr)
            continue

        elif conf >= conf_hard:
            # заходим сюда чтобы нииже не шла и непеределывала на СОФТ все
            if pay_old_status != 'HARD':
                new_status = 'HARD'
                update_payed(db, curr, xcurr, pay_in, pay_old_status, new_status, conf, shop_order, shop_order_addr)
        elif conf >= conf_soft:
            if pay_old_status != 'SOFT':
                new_status = 'SOFT'
                update_payed(db, curr, xcurr, pay_in, pay_old_status, new_status, conf, shop_order, shop_order_addr)


# вернем часть
def return_pay_ins_one(db, xcurr, pay_in, amount, ret_status=None):
    amount = Decimal(amount)
    if amount <= 0: return
    # проверим - а мож уже такая есть?
    pay_ins_return = db((db.pay_ins_return.xcurr_id == xcurr.id)
                    & (db.pay_ins_return.txid == pay_in.txid)
                    & (db.pay_ins_return.vout == pay_in.vout)).select().first()
    if pay_ins_return:
        # поидее такого не может быть что 2 раза возврат надо делать
        # Первый раз - если сумма платежа больше цены заказа и 2-й раз если заказ просрочен стал
        # так как все эти дела тольео в момент получания статуса TRUE у входа...
        # так как если делается возврат остатка - значит заказ ЗААКРЫТ и не может быть просрочен
        return
    # иначе добавим
    db.pay_ins_return.insert(
             ref_id = pay_in.id, xcurr_id = xcurr.id,
             in_block = pay_in.in_block, txid=pay_in.txid,
             vout = pay_in.vout,
             amount = amount,
             # addr тут не будем определять так как это может завесить надолго мож
             )
    pay_in.update_record( amo_ret = amount + (pay_in.amo_ret or Decimal(0)),
                         status = ret_status or pay_in.status)

def return_pay_ins(db, shop_order):
    for r in db(db.shop_order_addrs.shop_order_id == shop_order.id).select():
        # для тех транзакций что подходят под этот заказ-адресс и у которых уже статус TRUE
        # так как они больше уже не будут обрабатываться по приходу блоков
        # а те что будут - они там сами на автомате на возврат пойдут
        for pay_in in db((db.pay_ins.shop_order_addr_id == r.id)
                      & (db.pay_ins.status == 'TRUE')).select():
            amount = pay_in.amount - (pay_in.amo_ret or Decimal(0))
            if amount>0:
                xcurr = db.xcurrs[r.xcurr_id]
                return_pay_ins_one(db, xcurr, pay_in, amount, 'RETURNED')


##
# короче просроченными делаем только те у которых еще нет полной оплаты и срок прошел
# это можно по статусу СОФТ и ХАРД узнать - а ЗАКРЫТЫЕ должны быть удалены уже из стека
def check_expired(db):
    # для всех заказв что просрочены
    for st in db(db.shop_orders_stack.expire_on < datetime.datetime.now()).select():
        shop_order = db.shop_orders[st.ref_id]

        #if shop_order.price > shop_order.payed_hard + shop_order.payed_true and shop_order.status not in UNUSED_STATUSES:
        if shop_order.status not in [ 'SOFT', 'HARD' ]:
            # удалим, но со статусом погодим
            del db.shop_orders_stack[st.id]
            # этот заказ еще не проплачен полностью - делаем его просроченным
            set_status(db, shop_order, 'EXPIRED')
            return_pay_ins(db, shop_order)
            #print 'orders_lib.check_expired: shop_orders_stack %s deleted' % st.id
        else:
            # этот заказ уже оплачен хоть и не все подтверждены еще
            # ничего не делаем
            #print ' shop_order keep'
            continue


def orders_update(db, curr_block, curr, xcurr, conn):
    # заказы найдем те что просрочены
    #check_expired(db)
    # обновим все входы
    inputs_update(db, curr_block, curr, xcurr, conn)
