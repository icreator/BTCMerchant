# -*- coding: utf-8 -*-

if not request.is_local: raise HTTP(200, 'err')

def bill_show_update():
    return dict(h=DIV(LOAD('bill','show_update',args=request.args), _class='container'))

def serv_rates():
    import serv_rates
    serv_rates.get(db, not_local=True, interval=-1)


def index(): return dict(message="hello from tools.py")
