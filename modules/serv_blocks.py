#!/usr/bin/env python
# coding: utf8
#from gluon import *

Test = None

from time import sleep
import datetime

import db_common
import crypto_client
import serv_block_proc
import orders_lib
import rates_lib

def log(db, l2, mess='>'):
    print mess
    db.logs.insert(label123456789='shops_lib', label1234567890=l2, mess='%s' % mess)
def log_commit(db, l2, mess='>'):
    log(db, l2, mess)
    db.commit()

def run_blocks(db, not_local, interval=None):
    interval = interval or 20
    print __name__, 'not_local:',not_local, ' interval:', interval
    not_local = not_local == 'True'

    period3 = interval * 3 # 30sec
    period_m1 = interval * 6 # 1 min
    period_m3 = interval * 6*3 # 3min
    i_p3 = period3
    i_p_m1 = period_m1
    i_p_m3 = period_m3
    ##xconns = {} # запомним на 1 раз подключения
    ### теперь это обновляется ниже но не часто print 'Select xcurrs. If new xcurr added - restart me'
    xrecs = db(db.xcurrs.curr_id == db.currs.id).select() # один раз сделаем запрос
    while True:
        db.commit() # если предыдий проход с ошибклй - сохраним то что было перед нним
        print '\n', datetime.datetime.now()
        i_p3 = i_p3 + interval
        i_p_m1 = i_p_m1 + interval
        i_p_m3 = i_p_m3 + interval

        # по всем валютам обработаем блоки
        for rec in xrecs:

            if not rec.currs.used:
                # неиспользуемые будут при приходе блока обрабатываться
                # так мыж его отключили!
                continue

            ##conn = xconns.get(rec.currs.id) # из памяти попробуем взять
            conn = crypto_client.conn(rec.currs, rec.xcurrs)
            ##if not conn:
            ##     print 'try new conn to %s' % rec.currs.abbrev
            ##     conn = xconns[rec.currs.id] = crypto_client.conn(rec.currs, rec.xcurrs)
            if not conn: continue

            print rec.currs.abbrev

            # теперь блок проверим - если блок тот же то только 0-е подтвержд будут обработаны
            serv_block_proc.run_once(db, rec.currs.abbrev, None, None, conn, rec.currs, rec.xcurrs)
            # там внутри должно быть сохранение вычислено

            # так как долгие подключения к кошелькам могут быть то сохраняем для каждой крипты БД
            #db.commit()

        # теперь то что не так часто обрабатываем
        if i_p_m3 > period_m3:
            # обновим базу валют - мож там чего поменялось
            xrecs = db(db.xcurrs.curr_id == db.currs.id).select() # один раз сделаем запрос
            # старые заказы на обмен крипты удалим
        if i_p_m1 > period_m1:
            # просроченные заказы удалим из стека и присыоим статус - EXPIRED
            orders_lib.check_expired(db)
            rates_lib.check_orders(db)

        if not_local:
            pass
        else:
            #print 'local use - skeep serv_to_buy.proc_history and clients_lib.notify'
            pass

        if Test: break

        if i_p3 > period3:
            i_p3=0
        if i_p_m1 > period_m1:
            i_p_m1=0
        if i_p_m3 > period_m3:
            i_p_m3=0

        print 'sleep',interval,'sec'
        db.commit() # перед сном созраним все
        sleep(interval)

if Test: run_blocks(db)

# если делать вызов как модуля то нужно убрать это иначе неизвестный db
import sys
#print sys.argv
if len(sys.argv)>1:
    run_blocks(db, sys.argv[1], float(sys.argv[2]))
