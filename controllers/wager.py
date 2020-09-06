# -*- coding: utf-8 -*-

session.forget(response)

response.generic_patterns = ['*'] # json xml 
if request.extension == 'html':
    response.view = 'generic-col-9.html'

from time import sleep
from decimal import Decimal

import logging
logger = logging.getLogger("web2py.app.bs3b")
logger.setLevel(logging.ERROR) # DEBUG

def index():
    session.forget(response)
    r = UL('make', 'make_bet', 'close','solve')
    return dict(r=DIV(r, _class='container'))


# проверим аргумент и статус
def check_args(db, r, st = None, vars_check=[]):
    wager_id = r.args(0)
    if not wager_id: return 'Parameter (0) is empty', None, None
    wager = wager_id.isdigit() and db.wagers[wager_id]
    if not wager: return 'Wager [%s] not found' % wager_id, None, None
    if r.args(1) != wager.secr_key:
        sleep(3)
        return 'Parameter (1) is not valid', None, None
        
    if st and wager.status != st: return 'Wager status [%s] not is [%s]' % (wager.status, st), None, None
    
    vars = {}
    for key in vars_check:
        vol = r.vars.get(key)
        if vol:
            vars[key]=vol
        else:
            return 'Parameter [%s] is empty' % key, None, None

    return None, wager, vars

# это вызываем из сервера обработки ставок

# - выигравшие как паратметы идут
# wager/end/[wager_id]/[key]/951/953 - bills_id
def end():
    session.forget(response)
    err, wager, vars = check_args(db, request, 'RUN')
    if err: return { 'error': err }
    
    winned = request.args[2:]
    if len(winned) == 0: return { 'error': 'Winners list is empty' }
    
    # проверим счета и сколько заплочено - если ввобще не заплочено то отмена
    total = Decimal(0)
    winned_ok = []
    for bill_id in wager.bill_ids:
        bill = db.shop_orders[ bill_id ]
        if not bill: continue
        
        # проверим присутсвие игравших в начальном списке счтов
        if '%s' % bill_id in winned: winned_ok.append( bill_id )
            
        total += bill.payed_soft + bill.payed_hard + bill.payed_true
        
    if not total or total < 0: return { 'error': 'bets total == 0' }
    
    #return DIV(total,';', winned_ok)
    if len( winned_ok ) == 0: return { 'error': 'winned bills not passed' }

    wager.update_record( status = 'END', total = total, winner_ids = winned_ok )
    db.wagers_stack.insert( ref_id = wager.id, curr_id = wager.curr_id, status = 'END' )
    # --> serv_bloxk_proc --> wager_lib.solve
    return { 'status': 'OK' }

def go():
    session.forget(response)
    err, wager, vars = check_args(db, request, st = 'PAY')
    if err: return { 'error': err }

    wager.update_record(status = 'RUN')

    # все счета просмотрим и сделаем там закрытие - чтобы не могли больше платить на них
    # причем просто зададим цену счета - кто вперед заплатит с подтверждением тот и на коне
    # а те кто медленный платеж сделал пусть не успеют - цена закроется
    for bill_id in wager.bill_ids:
        bill = db.shop_orders[bill_id]
        if not bill: continue

        price = bill.payed_soft + bill.payed_hard + bill.payed_true
        if price:
            bill.price = price
            # и теперь надо проверьить на то что если все платежи ТРУЕ - то начисляить %% создателю ??
            # нет - это при выплате update_inputs(db,ee)
            if (bill.payed_soft + bill.payed_hard) == 0:
                ## если нет платежей на подходе то и статус у счетов закроем
                bill.status = 'CLOSED'
            bill.update_record()
                
        else:
            # если оплат нету - то просто сделаем его просроченным
            bill.update_record(status = 'EXPIRED', price = 1)

    return { 'status': 'OK' }

# показ просто перенаправим
# iframe - кстати можно впарамтерахзадать чтобы внутри странницы показывало
def show_bet_bill():
    session.forget(response)
    
    redirect(URL('bs3b','bill','show', args=request.args, vars = request.vars))

#создать счет для некотрого условия по спору
# здесь все параметры как у создания счета + номер споря + номер условия
# если номер спора не задан о созддадим его сразу
def make_bet_bill():
    session.forget(response)
    err, wager, vars = check_args(db, request, st = 'PAY')
    if err: return { 'error': err }

    
    ## да - тут надо комисиию себе оставить - остальное сохранить пока
    request.vars['keep'] = wager.keep
    
    request.vars['public'] = 1 # сделаем иих открытыми всем
    curr = db.currs[wager.curr_id]
    request.vars['curr'] = curr.abbrev
    request.vars['curr_in'] = curr.abbrev ## !!! только таже что и на входе - иначе кому высылать не понятно будет
    
    # Перезапишем аргументы для создания счета
    request.args[0] = '%s' % wager.shop_id # в строку преобразуем а то там прием адреса кошелька тестируется
    
    from cp_api import make as make_bill
    #print request.args, request.vars
    err, bill_id = make_bill(db, request)
    if err: return { 'error': err }

    # просто добавим к списку условий номер счета - без ключа секретного даже
    wager.bill_ids.append(int(bill_id))
    wager.update_record(bill_ids = wager.bill_ids )
    
    return { 'bill': '%s' % bill_id }

# необходимо сразу создать спор - чтобы потом случайнно разныее споры не создались когда
# разныее нажмутодновременнно созддать спорт - нужно чтобы кто-то один создавал
# make/SHOP/CURR
def make():
    session.forget(response)

    shop_id = request.args(0)
    if not shop_id: return { 'error': 'Parameter [0] is empty - SHOP_ID'}
    shop = db.shops[shop_id]
    if not shop: return { 'error': 'Shop[%s] not found' % shop_id }
    curr = request.args(1)
    if not curr: return { 'error': 'Parameter [1] is empty - CURRENCY' }
    curr = db(db.currs.abbrev == curr ).select().first()
    if not curr: return { 'error': 'Currency [%s] not found' % curr }

    import random
    import string
    key = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for x in range(10))
    
    print request.vars
    wager_id = db.wagers.insert(
                shop_id = shop_id, curr_id = curr.id, secr_key = key,
                keep = Decimal(1) - Decimal(request.vars.fee or 0 ) * Decimal(0.01), # service fee 0 - 3%
                run_dt = request.vars.run_dt,
                maker_fee = Decimal(request.vars.m_fee or 1) * Decimal(0.01), # maker fee = 1-3 %
                maker_addr = request.vars.m_addr,
                )
    
    return {'wager': wager_id, 'key': key }
