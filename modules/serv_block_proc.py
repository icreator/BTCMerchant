#!/usr/bin/env python
# coding: utf8
import datetime
from decimal import Decimal

from gluon import current
T = current.T

import common
import crypto_client
import shops_lib
import db_client
import wager_lib

#
# на самом деле это не сервер - он не висит постоянно в памяти и не выполняется параллельно
# просто при приходе блока вызывчается curl со ссылкой на страницу проекта
# start /MIN curl http://127.0.0.1:8000/ipay3/tools/block_proc/%1/%2 -s >nul
# see !notify-curl.cmd in C:\web2py\applications\ipay4\wallets
# see bitcoin.conf and !notify.cmd in ./bitcoin

def log(db, l2, mess='>'):
    m = 's_block_proc'
    mess = '%s' % mess
    print m, '[%s]' % l2, mess
    db.logs.insert(label123456789 = m, label1234567890 = l2, mess = mess)
def log_commit(db, l2, mess='>'):
    log(db, l2, mess)
    db.commit()

def return_trans(db, in_block, curr, xcurr, addr, acc, amo, txid, vout):
    amo = amo - xcurr.txfee
    if amo < xcurr.txfee:
        # остаток мизерный не высылаем
        return
    print 'unknown [%s] address %s for account:"%s"' % (curr.abbrev, addr, acc)
    # если не найдено в делах то запомним в неизвестных
    # на отсылку обрано - может заказ уже просрочен а платеж только пришел
    db.pay_ins_return.insert(
            xcurr_id = xcurr.id,
            in_block = in_block,
            amount = amo, # тут уже за минусом комиссии возврат
            txid=txid, vout=vout,
            )
    return True

def b_p_db_update( db, conn, curr, xcurr, tab, curr_block, not_ret=None):

    to_commit = None
    ret = not not_ret # не возвращать - если тестовый вызов
    # сюда приходят все наши входы - запомнить их
    #orders_update = {}
    #main_addrs = cn.getaddressesbyaccount('.main.')
    #conf_addrs = cn.getaddressesbyaccount('.confirm.')

    for rec in tab: #.iteritems():
        amo = rec['amo']
        acc = rec['acc']
        addr = rec['addr']
        txid = rec['txid']
        vout = rec['vout']
        confs = rec['confs'] # если 0 - то не используем ее для возврата и подтверждения изменения инфо и прочее
        in_block = curr_block - confs + 1 # тут может быть старая транзакция с ХХ подтверждениями
        #if len(acc)==0:
        #    # пропустим пустые а то они все будут подходить
        #    continue
        #print xcurr.abbrev, 'acc:"%s"' % acc, ' unspent:',amo
        #print datetime.datetime.fromtimestamp(rec['time'])
        #print rec, '\n'
        # тут если крипта не используется - то все они будут отвергнуты
        shop_order_addr = curr.used and db((db.shop_order_addrs.addr==addr)
            & (db.shop_order_addrs.xcurr_id==xcurr.id)).select().first()

        if not shop_order_addr:
            # такого адреса у нас нет пропустим...
            if confs>0:
                # только для тех что подтверждены - чтобы дважды проводки не записывались
                if acc == '.main.':
                    # если это приход на  главный адрес - например пополнения с обмена\
                    # то такую проводку пропустим
                    continue
                elif acc == '.confirm.':
                    # если это вход для подтверждения изменения клиентских данных
                    shops_lib.try_confirm_changes(db, xcurr, txid, vout)
                    to_commit = True
                    # и сразу их вернем обратно
                # тут если на выходе Ноне то берем старый to_commit
                to_commit = ret and return_trans(db, in_block, curr, xcurr, addr, acc, amo, txid, vout) or to_commit
            # берем следующую проводку
            continue
        elif shop_order_addr.unused and confs>0:
            # тут если на выходе Ноне то берем старый to_commit
            to_commit = ret and return_trans(db, in_block, curr, xcurr, addr, acc, amo, txid, vout) or to_commit
            continue

        # теперь в таблице от unspent без повторов - так как там блок каждый раз новый
        trans = db((db.pay_ins.txid==txid) & (db.pay_ins.vout==vout)).select().first()
        if trans:
            #print 'b_p_db_update exist:', amo, txid, vout
            if confs>0:
                # уже такая есть и она с подтверждением
                to_commit = True
                # если она была внесена с 0-м подтверждением то исправим у нее блок
                # а статус поменяется дальше при осмотре заказов
                ################################# &&****&&&&&???????
                print 'pay_ins %s in_block %s updated' % (amo, in_block)
                trans.update_record(in_block = in_block)
                tr_stack = db(db.pay_ins_stack.ref_id==trans.id).select().first()
                if tr_stack:
                    # ну запись в стеке изменим тоже
                    tr_stack.update_record(in_block = in_block)
            # следующую берем запись
            continue

        to_commit = True
        created_on = datetime.datetime.fromtimestamp(rec['time'])
        #print 'block_proc - db.pay_ins.insert', created_on

        pay_id = db.pay_ins.insert(
            shop_order_addr_id = shop_order_addr.id,
            amount = amo,
            in_block = in_block,
            txid=txid, vout=vout,
            created_on = created_on,
            )
        db.pay_ins_stack.insert(
            ref_id = pay_id,
            xcurr_id = xcurr.id,
            in_block = in_block,
            )

        '''
        #orders_update[shop_order_addr.shop_order_id]=1 # запомним заказы которые надо обновить
        # тепеь данные по этой крипте для этого заказ обновим
        shop_order_addr.update_record(amount = shop_order_addr.amount + amo,
                in_block = in_block,
                amo_out = shop_order_addr.amo_out + amo_out
                )
        '''

    return to_commit # сообщим - надо ли базу сохранять

# TODO
# тут по 2 раза выдает выходы если они сгенерированы
# проверка - по
# http://127.0.0.1:8000/shop/tools/proc_unspent/BTC/3333/1MfMcg8J7rKKGUNmGRvEhHCZHiqPzdAzoB
# 
##############
# найдем все входы крипты на адреса наших заказов
# на выходе массив по входам
# тут от 0 до conf вглуь + генерация на 120 блоков старше
# тоесть берутся ссамые свежие входы
def b_p_proc_unspent( db, conn, curr, xcurr, conf=None, addr_in=None ):
    #print 'BALANCE:', conn.getbalance(), addr_in and (' for addr_in:',conn.getbalance(addr_in)) or 'addr_in=None'
    # проверим непотраченные монеты на адресах,
    # которые созданы для приема крипты
    #
    # тут ограничиваем просмотр входящих неизрасходованных
    # транзакций по подтверждениям с учетом номера обработанного блока
    # с заданием макс_подтв так чтобы не брать уже обработанные
    # а начинаем всегда 1-го подтверждения, потом будем уже разбирать кол-во подтверждений
    tab = []

    conf = conf == None and 1 or conf # если пусто то по умолчанию с одним подтверждением
    if conf:
        lUnsp = conn.listunspent( 0, conf) # например с 1-го по 1й
        #print '\n******************\n lUnsp(0, %s):' % conf
        #for r in lUnsp: print r
        if type(lUnsp) == type({}):
            # ошибка
            log(db, 'b_p_proc_unspent', 'listunspent %s' % lUnsp)
            return tab
        # теперь для вновь появившихся сгенерированных
        # они появлюяются в unspent через 120 подтверждений
        conf_gen = xcurr.conf_gen or 120
        if conf_gen < conf:
            # если с подтверждения больше чем подт_генерации то сдвинем их
            conf_gen = conf + 1
        l_generate = conn.listunspent( conf_gen, conf_gen + conf - 1) # например с 120-го по 120й
        #print '\n l_generate:\n'
        #for r in l_generate: print r
        lUnsp += l_generate
    else:
        # блок = -1 значит ищес неподтвержденные  только
        lUnsp = conn.listunspent( 0, 0)
        if type(lUnsp) == type({}):
            # ошибка
            log(db, 'b_p_proc_unspent', 'listunspent %s' % lUnsp)
            return tab

    #for r in lUnsp: print '\n',r
    #print len(lUnsp)
    
    for r in lUnsp:
        # выдает входящие транзакции причем те что не израсходовались
        # берем только подтвержденные нами и только входы - у них нет выходов в транзакции
        # иначе это сдача от выхода

        acc = r.get(u'account')
        if acc and acc == '.main.': continue # свои проводки не проверяем

        txid = r[u'txid']
        ti = conn.gettransaction(txid)

        # тут массив - может быть несколько транзакций
        # может быть [u'category'] == u'receive' ИЛИ u'send'
        trans_details = ti['details']
        #log(db, 'b_p_proc_unspent', 'trans_details %s' % trans_details)
        # так вот, в одной транзакции может быть несколько входов!
        # оказывается и с 1м есть выход в деталях - сдачи может и не быть
        its_outcome = False
        for detail in trans_details:
            if detail[u'category'] == u'send':
                its_outcome = True
                # сдача тут
                break
        if its_outcome:
            continue

        amo = r[u'amount']
        vout = r[u'vout']
        addr = r.get(u'address')
        if not addr:
            # если адреса нет то берем его из рав-транзакции
            rawtr = conn.getrawtransaction(txid, 1)
            vouts = rawtr[u'vout']
            trans = vouts[vout]
            #print trans
            addr = trans[u'scriptPubKey'][u'addresses'][0]

        if addr_in and addr_in != addr: continue
        if not acc:
            acc = conn.getaccount(addr)
        #print acc, addr
        #print amo, txid, vout
        # запомним сумму монет на вывод
        tab.append({
            'acc': acc, 'amo': amo,
            'confs': r[u'confirmations'],
            # запомним данные для поиска потом
            'txid':txid, 'vout': vout,
            'addr': addr,
            'time':ti[u'time']})

    return tab

# берем адреса на возврат или выплату из таблицы и
# формируем send_many
#  комиссию тут не учитываем - не вычитаем ! - при создании записей на возврат это надо делать??
# эта функция в других модулях не используется
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
        if amo >0:
            # с накоплением на тот же адрес обязательно!
            addrs[sender_addr] = (addrs.get(sender_addr) or 0.0) + amo
        vol += amo
        ids.append( [r.id, r.ref_id, r.amount] )
        #txid = conn.sendtoaddress(sender_addr, amo )
        #print txid

    if len(ids)==0: return
    # собрали все кому надо вернуть
    lim = float(xcurr.txfee) * 2
    if vol < lim:
        print 'serv_block_prov: refused vol so small', vol, '<',lim
    else:
        # если размер выплат больше чем комиссия
        # то попытаемся их выплатить
        res = crypto_client.send_to_many(db, curr, xcurr, addrs)
        log(db, 'return_refused', 'RETURN res: %s' % res)
        txid = res and res.get('txid')
        if txid:
            # если выплата прошла то удалим записи
            for ret_rec in ids:
                del table[ret_rec[0]]
                db.pay_ins_returned.insert(ref_id = ret_rec[1], amount = ret_rec[2],
                           txid=txid)
            db.commit()
        return txid
    return


import db_common
import orders_lib

def run_once(db, abbrev, from_block_in=None, addr_in=None, conn=None, curr=None, xcurr=None, not_ret=None):
    if not curr:
        curr, xcurr, _ = db_common.get_currs_by_abbrev(db, abbrev)
    if not xcurr:
        mess = "ERROR: (run_once) " + abbrev + " in db.xcurrs not exist"
        print mess
        return

    tab = None
    conn = conn or crypto_client.conn(curr, xcurr)
    if not conn: return
    
    e = '---'
    conf = -1
    to_commit = None
    old_block = curr_block = from_block_in or xcurr.from_block # сохраним для проверки появления нового блока
    if old_block == None: old_block = 1
    #try:
    if True:
        # тут же надо взять курсы для транзакций что не по ордеру пришли
        # придется курсы обмена брать не по объему а по % тут
        #addr_in= None #'4V6CeFxAHGVTM5wYKhAbXwbXsjUW5Bazdh'
        #from_block_in = None #65111
        # ищем все входы кроме на аккаунт '.main.'
        curr_block = conn.getblockcount()
        print curr_block
        if type(curr_block) != type(1):
            # ошибка при получении блока
            return
        conf = curr_block - old_block
        if conf < 0:
            # не обрабатывать
            return
        elif conf >0:
            # новый блок пришел - уже надо сохраняться
            xcurr.update_record(from_block = curr_block)
            # значит и баланс мог поменяться - там проводки могли получить новый статус
            balance = crypto_client.get_reserve(curr, xcurr, conn)
            curr.update_record(balance = balance)
            to_commit = True
            print '  conf:', conf

        e = '---'
        tab = b_p_proc_unspent(db, conn, curr, xcurr, conf, addr_in)
        if len(tab)>0:
            # здесь закатываем все в базу и курс по заказам тоже в транзакции
            to_commit1 = b_p_db_update(db, conn, curr, xcurr, tab, curr_block, not_ret)
            to_commit = to_commit or to_commit1
            # тут же обновим информацию в заказах
            ### нет - они все только что поступили orders_lib.orders_update(db,  orders_update_list)
            ### а надо обновлять те платежи которые уже ДОНЕ и  сних переводить магазинам
            ### так сто зедсь коммит()
        if to_commit: db.commit()
    #except Exception as e:
        if to_commit: db.rollback()
        if e != '---': log(db, 'ERR:run_once/b_p_db_update', '%s' % e)

    if conf == -1:
        # выше была ошибка с подключением  то и не идем дальше
        return

    e = '---'
    #try:
    if True:
        # обновим статусы заказов если есть необновленные
        orders_lib.orders_update(db, curr_block, curr, xcurr, conn)
        db.commit()
    #except Exception as e:
        db.rollback()
        if e != '---': log(db, 'ERR:run_once/orders_lib.orders_update', '%s' % e)

    if conf == 0:
        # если это не новый блок то и не идем дальше
        return
    
    e = '---'
    #try:
    if True:
        # если есть транзакции не включенные еще в блок
        wager_lib.solve(db, curr, xcurr, conn)
        db.commit()
    #except Exception as e:
        db.rollback()
        if e != '---': log(db, 'ERR:run_once/wager_lib.solve', '%s' % e)

    e = '---'
    try:
    #if True:
        pass
        # если есть транзакции не включенные еще в блок
        #crypto_client.re_broadcast (db, curr, xcurr, conn)
        #db.commit()
    except Exception as e:
        #db.rollback()
        if e != '---': log(db, 'ERR:run_once/crypto_client.re_broadcast', '%s' % e)

    e = '---'
    try:
    #if True:
        # теперь вернем все что не наше обратно
        # и выплатим магазинам их доход
        # поидее это все надо в одну транзакцию запихать
        txid = return_refused(db, curr, xcurr, conn, curr_block, db.pay_ins_return)
        db.commit()
    except Exception as e:
        db.rollback()
        if e != '---': log(db, 'ERR:run_once/return_refused', '%s' % e)
    
    e = '---'
    #try:
    if True:
        pass
        # если накопилось крипты на депозитах магазинов много то выплатим тут сразу
        shops_lib.withdraw(db, curr, xcurr, conn, curr.withdraw_over) # тут может крипты не хватить так как обмен нужен еще
        ### там внутри есть сохранение db.commit() # здесь нужно сохранение так как идут выплаты во вне
    #except Exception as e:
        ###db.rollback()
        if e != '---': log(db, 'ERR:run_once/shops_lib.withdraw', '%s' % e)
