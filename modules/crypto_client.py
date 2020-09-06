#!/usr/bin/env python
# coding: utf8

# TODO
## при определнии адреса отправителя - если нет связи с кошельком - выход
import logging
logger = logging.getLogger("web2py.app.bs3b")
logger.setLevel(logging.DEBUG)

#!/usr/bin/python2
from gluon import current
T = current.T
cache = current.cache

#from jsonrpc import ServiceProxy
from authproxy_my import AuthServiceProxy as ServiceProxy
ROUND_TO = 8

def log(db, l2, mess='>'):
    m = 'crypto_client'
    print m, l2, mess
    db.logs.insert(label123456789=m, label1234567890=l2, mess='%s' % mess)
def log_commit(db, l2, mess='>'):
    log(db, l2, mess)
    db.commit()

# покажем если был вызов а не из кэша
def conn_1(curr, xcurr):
    print 'try connect to ',curr.abbrev
    # def __init__(self, service_url, service_name=None, timeout=HTTP_TIMEOUT, connection=None):
    cn = ServiceProxy(xcurr.connect_url, None, 60)
    #print cn
    blk = cn.getblockcount()
    print 'connected on block:', blk
    return cn

# тут если удача то надолго запомним
def conn_0(curr, xcurr):
    try:
        cn = cache.ram(curr.abbrev, lambda: conn_1(curr, xcurr), time_expire = 36000)
    except Exception as e:
        print curr.abbrev + ' conn except: %s' % str(e).decode('cp1251','replace')
        cn = None
    if not cn:
        cache.ram.clear(curr.abbrev)
    return cn

# если нет связи то тоже запомним на небольшое время
def conn(curr, xcurr, cn=None):
    # пока не подключимся - пробуем
    cn = cache.ram(curr.abbrev + '_0', lambda: conn_0(curr, xcurr), time_expire = 10)
    return cn

# выдать резервы только с учкетом проверенного блока на вход -
# так чтобы нельзя было
# перевести еще неучтенные монеты со входов UNSPENT
def get_reserve(curr, xcurr, cn=None):
    if not cn:
        cn = conn(curr,xcurr)
    if not cn:
        return
    curr_block = cn.getblockcount()
    conf = curr_block - xcurr.from_block + xcurr.conf_hard + 1
    #print conf
    tab, sum_Full = get_unspents(cn, conf)
    #print sum_Full
    return sum_Full

def get_tx_info(conn, txid, pars=None):
    res = None
    try:
        ##res = conn.getrawtransaction(txid,1) # все выдает
        res = conn.gettransaction(txid) # выдает только для кошелька
        ##res = res and res.get('details')
    except Exception as e:
        res = { 'error': e }
        pass
    return res
def get_rawtx_info(conn, txid, pars=None):
    res = None
    try:
        res = conn.getrawtransaction(txid,1) # все выдает
    except Exception as e:
        res = { 'error': e }
        pass
    return res

def trans_exist(conn, txid):
    res = None
    #try:
    if True:
        # здесь нельзя делать отлов ошибок связи
        # иначе выдаст что нет транзакции хотять неизвестно - просто вязи небыло
        #res = conn.getrawtransaction(txid,1) # все выдает
        res = conn.gettransaction(txid) # выдает только для кошелька
        res = res and res.get('details')
    #except Exception as e:
    else:
        ###res = { 'error': e }
        pass
    return res

def is_not_valid_addr(cc, addr):
    valid = cc.validateaddress(addr)
    if not valid or 'isvalid' in valid and not valid['isvalid'] or 'ismine' in valid and valid['ismine']:
        return True

def send(db, curr, xcurr, addr, amo, conn_in=None):
    cc = conn_in or conn(curr, xcurr)
    if not cc: return {'error':'unconnect to [%s]' % curr.abbrev }, None
    if is_not_valid_addr(cc, addr):
        return {'error':'invalid [%s] address' % curr.abbrev }, None
    try:
        # проверим готовность базы - is lock - и запишем за одно данные
        log_commit(db, 'send', '%s[%s] %s' % (amo, curr.abbrev, addr))
        res = cc.sendtoaddress(addr, amo)
        bal = get_reserve(curr, xcurr, cc)
    except Exception as e:
        return {'error': str(e).decode('cp1251','replace') + ' [%s]' % curr.abbrev }, None
    #print "SEND:", res
    return res, bal

def get_xaddress_by_label(conn, label):

    addrs = conn.getaddressesbyaccount( label )

    if addrs:
        return addrs[0]
    return conn.getnewaddress( label )

def get_main_addr(cn):
    addr = cn.getaddressesbyaccount('.main.')
    if addr:
        # берем тот что уже есть
        addr = addr[0]
    else:
        # берем новый
        addr = cn.getaccountaddress('.main.')
    return addr

def get_confirm_addr(cn):
    addr = cn.getaddressesbyaccount('.confirm.')
    if addr:
        # берем тот что уже есть
        addr = addr[0]
    else:
        # берем новый
        addr = cn.getaccountaddress('.confirm.')
    return addr

# открыть те что в списке
def unlocks(conn, tab=None):
    if not tab: tab = conn.listlockunspent() # все закрытые откроем
    conn.lockunspent(True, tab)

# закрыть все входы, чтобы при переносе монет они не трогались
def locks(conn):

    lu = conn.listunspent(0)
    ll = []
    for u in lu:
        ll.append({u'txid':u[u'txid'], u'vout':u[u'vout']})
    try:
        conn.lockunspent(False, ll)
    except Exception as e:
        print e,
        print e.error

# найти адреса того кто выслал их
# и сумму входа с этого адреса
def sender_addrs(conn, tr, with_amo=None):
    tr_info = conn.getrawtransaction(tr,1)
    #print 'sender_addrs tr_info:', tr_info
    vins =  tr_info and 'vin' in tr_info and tr_info['vin']
    #print 'sender_addrs vins:', vins

    if not vins:
        #res.append({ 'tr_info.vins': 'None'})
        # тут может быть приход с добвтого блока - тогда тоже будет пусто!
        mess = 'not found vins - RUN "demon"  -reindex -txindex ?? %s' % tr_info
        print 'sender_addrs() ', mess
        logger.error( mess )
        return { 'error': 'tx_info not exist in blockchain' }
    senders = []
    #print 'VINS:', vins
    for vin in vins:
        if 'coinbase' in vin or 'txid' not in vin:
            # это генерация
            if 'GENERATED' not in senders:
                senders.append('GENERATED')
            continue
        txid = vin['txid']
        vout = vin['vout']
        #print vin
        tr_in_info = conn.getrawtransaction(txid,1)
        #print vout, tr_in_info[u'vout'][vout][u'value']

        if 'error' in tr_in_info:
            print 'RUN "C:\Program Files (x86)\CopperLark\CopperLark.exe"  -reindex -txindex'
            logger.error( 'ERROR: %s -- for txid: %s, ' % (tr_in_info, txid) )
            continue
        addrs = tr_in_info[u'vout'][vout][u'scriptPubKey'][u'addresses']
        for a in addrs:
            if a not in senders:
                if with_amo:
                    #print tr_in_info
                    senders.append([a, tr_in_info[u'vout'][vout][u'value']])
                else:
                    senders.append(a)
    return senders

def sender_addr(conn, tr):
    
    vv = -1
    kk = None
    for r in sender_addrs(conn, tr, True):
        if vv < r[1]:
            kk = r[0]
            vv = r[1]

    return kk

# выдать неиспользованные входы - для создания транзакции вручную
# наберем входы на данный баланс и для данного адреса
# addrs = [...]
# причем берутся входы от conf_from и старше - тоесть вглубь
# тоесть берутся самые старшие входы
def get_unspents(conn, conf_from=None, vol=None, addrs=None, accs=None, xcurr=None):
    conf_from = conf_from == None and 1 or conf_from # если на входе 0 то не менять
    sumFull = sumReceive = sumChange = sumGen = 0.0
    tab = []
    lUnsp = conn.listunspent(conf_from)
    #print '\n+++++++++++\n lUnsp:'
    #for r in lUnsp: print r

    # тут генерированные транзакции тоже включены

    # обработка со старых начинаем
    lUnsp.sort(key=lambda r: r[u'confirmations'], reverse=True)
    #print len(lUnsp)
    #print conf_from, conn.getbalance(), lUnsp
    for unsp in lUnsp:
        #print 'conf:', unsp[u'confirmations'], ' amo:', unsp[u'amount'], 'vout:',unsp[u'vout']

        txid = unsp['txid']
        ti = conn.gettransaction(txid)
        trans_details = ti['details']

        vout = unsp[u'vout']

        tx_addr = unsp.get(u'address')
        if addrs and tx_addr not in addrs: continue

        tx_acc = unsp.get(u'account')
        if not tx_acc:
            tx_acc = conn.getaccount(tx_addr)
        if accs and tx_acc not in accs: continue

        amo = float(unsp[u'amount'])
        #print '\n\n confirmations:',unsp[u'confirmations'], 'amo:',amo, unsp

        #print '   DETAILS', trans_details
        categ = ''

        its_change = None
        for detail in trans_details:
            if detail[u'category'] == u'send':
                # если тут хоть один выход встретился - значит это сдача
                # и она тут как вход
                sumChange = sumChange + amo
                its_change = True
                categ = 'change'
                break

        if not its_change:
            # если это не сдача то смотрим еще категорию "сгенерировано"
            its_generate = False
            for detail in trans_details:
                if detail[u'category'] == u'generate':
                    # сюда пришло если монета сгенерирована - ждем больше подтверждений
                    its_generate = True
                    categ = 'generate'
                    break

            if its_generate:
                sumGen = sumGen + amo
            else:
                categ = 'receive'
                sumReceive = sumReceive + amo


        sumFull = sumChange + sumGen + sumReceive
        tab.append({
                    'txid':txid, 'vout':vout,
                    'category': categ, 'amo': amo,
                    'acc': tx_acc,
                    'confs': unsp[u'confirmations'],
                    'addr': tx_addr,
                    'time':ti[u'time'],
                    })
        #print '   appended... as', categ
        if vol and vol < sumFull: break

    #sumFull = sumFull + sumChange + sumGen + sumReceive
    #print sumFull, 'change:', sumChange, 'gen:',sumGen, 'receive:',sumReceive
    return tab, sumFull

# вычислить комисиию за длинну транзакции
def calc_txfee(cn, lus, sends, fee_in):
    tx_str = cn.createrawtransaction (lus, sends)
    #print 'len(tx_str):',len(tx_str), fee_in
    return fee_in*(round(len(tx_str)/1000, 0) + 1)

def send_to_many(db, curr, xcurr, sends_in, tx_fee_in=None, conn_in=None):
    if len(sends_in)==0: return
    # тут надоп роверить баланс клиента
    vol = 0.0
    sends = {}
    for (k,v) in sends_in.iteritems():
        v = round(float(v),ROUND_TO)
        vol = vol + v
        # отловим повторы в списке и ссумируем их
        # хотя поидее они уже там из списка просуммированы
        sends[k] = (sends.get(k) or 0.0) + v # converted to float

    if vol < float(xcurr.txfee) * 3:
        return {'error': 'ERROR: so small amo to send' }
    cn = conn_in or conn(curr,xcurr)
    if not cn:
        return {'error': 'ERROR: connection to wallet [%s] is broken' % curr.abbrev }

    #print 'wallet balance:', cn.getbalance()
    res = None
    addr=None
    # наберем входы неиспользованные на этот объем монет
    lus, amo_u = get_unspents(cn, xcurr.conf_true, vol, addr)
    #print lus
    transFEE = calc_txfee(cn, lus, sends, float(tx_fee_in or xcurr.txfee or 0.0001))
    #print transFEE

    # заново наберем чтобы комиссию включить
    lus, amo_u = get_unspents(cn, xcurr.conf_true, vol + transFEE, addr)

    # теперь надо остаток перевести себе за минусом комиссиии платежа
    my_change = round(amo_u - vol - transFEE, 8)
    #print vol, '+ my_change:', my_change, len(lus), len(sends), amo_u
    if my_change < 0:
        return { 'error': 'ERROR: my_change %s < 0 ! wallet balance: %s - %s - fee %s' % (my_change, amo_u, vol, transFEE) }
    if my_change > 0:
        # тут остается сдача, поэтому
        # добавим наш адрес для возврата сдачи, остальное уйдет как комиссия за транзакцию
        ### если на старый адресс пихать или даже брать новый
        # то баланс в кошельке до подтверждения блока будет в неподтвержденных!
        # тут надо использовать
        change_addr = get_main_addr(cn)
        #print change_addr, '=', my_change
        sends[change_addr] = my_change

    tx_str = cn.createrawtransaction (lus, sends)
    if type(tx_str) == type( {} ):
        #print tx_str
        return { 'error': 'ERROR: createrawtransaction res= %s' % (tx_str) }

    #return '%s' % transFEE

    #print '\n\n [%s]' % cn.decoderawtransaction(tx_str)

    # провеим нне залочена ло база данных и заодно запомним платеж в логах
    if db: log_commit(db, 'send_to_many', 'try crypto_client.send_to_many %s: %s' % (curr.abbrev, sends_in))

    res = cn.signrawtransaction( tx_str )
    #print 'signrawtransaction:', res
    if u'error' in res or not res[u'complete']:
        return { 'error': 'ERROR: signrawtransaction %s' % (res[u'error']), 'pars': {'lus': lus, 'sends': sends} }
    # транзакция успешно подписана - можем отправить ее в сеть

    tx_hex = res[u'hex'] # запомним ее - вдруг сеть не включила в блок
    res = cn.sendrawtransaction( tx_hex )
    #print type(res)
    #log(db, 'send_to_many', 'sendrawtransaction: %s' % res)
    if type(res) != type(u' '):
        return { 'error': 'ERROR: sendrawtransaction %s' % (res), 'pars': {'lus': lus, 'sends': sends} }

    return { 'txid': res, 'tx_hex': tx_hex, 'txfee': transFEE }

## https://en.bitcoin.it/wiki/Raw_Transactions
def re_broadcast (db, curr, xcurr, cn=None):
    return # поидее наш кошелек сам все делает
    cn = cn or conn(curr,xcurr)
    if not cn: return

    ok_conf = 6
    for r in db((db.xcurrs_raw_trans.xcurr_id==xcurr.id)
        & (db.xcurrs_raw_trans.confs < ok_conf)).select():

        tx = cn.getrawtransaction (r.txid,1)
        confs = tx.get('confirmations')
        if confs>0:
            r.confs = confs
            r.update_record()
            continue
        #log(db, 're_broadcast', tx)
        res = cn.sendrawtransaction(tx[u'hex'])
        print 're_broadcast', res

def re_broadcast_bills_draws_trans (db, curr, xcurr, cn=None, only_get_confs=True):
    cn = cn or conn(curr,xcurr)
    if not cn:
        print 'not conn'
        return

    for r in db((db.bills_draws_trans.curr_id==curr.id)
        & ((db.bills_draws_trans.confs == None)
        | (db.bills_draws_trans.confs == 0))).select():

        print curr.abbrev, r.txid
        tx = cn.getrawtransaction (r.txid,1)
        confs = tx.get('confirmations')
        if confs>0:
            r.confs = confs
            r.update_record()
            print 'new conf updated', confs
            continue
        ##log(db, 're_broadcast', tx)
        res = only_get_confs and {'txid': r.txid, 'result':'only_get_confs!'}
        ##res = res or cn.signrawtransaction(tx[u'hex']) - просто подписывает без отсылки
        res = res or cn.sendrawtransaction(tx[u'hex'])
        print res

    db.commit()
