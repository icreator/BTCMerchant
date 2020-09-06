#!/usr/bin/env python
# coding: utf8
from gluon import *

# взять несколько записей рекламы случайно
def get(db, limit, level=None):
    # если уровнь задан то брать только с ним и что выше
    level = level or 0
    recs = db(level <= db.recl.level_
        ).select(db.recl.ALL,orderby='<random>', limitby=(0, limit))
    #recs.update ( count = count + 1 )
    #print recs
    ht = ''
    for r in recs:
        r.count = r.count +1
        r.update_record()
        ht = ht + '<br>' + r.url
    return recs, XML(ht)
