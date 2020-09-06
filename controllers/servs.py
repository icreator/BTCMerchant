# coding: utf8
import common
# запустим сразу защиту от внешних вызов
if common.not_is_local(): raise HTTP(200, T('ERROR'))

from time import sleep
import datetime

# это для CRON - но он чето не работает

import db_common

interval = 10
def all_blocks():
    session.forget(response)
    return

    curr,xcurr,_ = db_common.get_currs_by_abbrev(db, 'CLR')
    dd = 10
    while dd>0:
        dd = dd - 1
        print '\n', dd, datetime.datetime.now()
        xcurr.update_record(from_block = xcurr.from_block + 1)
        db.commit()
        sleep(interval)

def index(): return 'sss'
