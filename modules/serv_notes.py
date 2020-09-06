#!/usr/bin/env python
# coding: utf8
from gluon import *

Test = None

from time import sleep
import datetime

import db_common
import shops_lib

def log(db, l2, mess='>'):
    print mess
    db.logs.insert(label123456789='s_notes', label1234567890=l2, mess='%s' % mess)
def log_commit(db, l2, mess='>'):
    log(db, l2, mess)
    db.commit()

def run_once(db):
    return shops_lib.notify(db)

def run(db, not_local, interval=None):
    interval = interval or 60
    print __name__, 'not_local:',not_local, ' interval:', interval
    not_local = not_local == 'True'
    
    e=None
    period3 = interval * 10
    i_p3 = period3
    while True:
        print '\n', datetime.datetime.now()
        
        if True:
        #try:
            # пошлем уведомления
            res= run_once(db)
            #print res
            db.commit()
        #except Exception as e:
        #    db.rollback()
        #    if e: log_commit(db, 'run', 'shops_lib.notify ERROR: %s' % e)

        if Test: break
        print 'sleep',interval,'sec'
        db.commit() # перед сном созраним все
        sleep(interval)

if Test: run(db)

# если делать вызов как модуля то нужно убрать это иначе неизвестный db
import sys
#print sys.argv
if len(sys.argv)>1:
    run(db, sys.argv[1], float(sys.argv[2]))
