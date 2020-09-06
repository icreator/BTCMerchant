# coding: utf8

session.forget(response)
#if request.extension == 'html' and request.function != 'index':
if request.extension == 'html':
    response.view = 'generic-col-9.html'

import time

# здесь вызовы могут быть в 3-х форматах;
# .html
# .json
# .xml
# у каждого надо создать свовй вид со своим расшириением задать response.generic_patterns
# http://127.0.0.1:8000/shop2/api/get_reserves.json

# разрешить использовать виды generic.*
# в локальном режиме все - в том числе и .html - который дает доступ к статистике
# не в локальном только .json и .xml
##response.generic_patterns = ['*'] if request.is_local else ['*.json','*.xml']
# там в генерик-файле стоит проверка на локальный вызов - так что можно разрешить
response.generic_patterns = ['*']

def show_item(k, u, v):
    return DIV(
            DIV(
                DIV(H3(k),
                    _class='col-sm-3'),
                DIV(
                    v,
                    _class='col-sm-9', _style='background-color:#DDD;'),
                _class='row', _style='background-color:#FDA;'),
            _class='row',
            _onclick="location.href='%s'" % u,
            _style='margin-bottom:15px;cursor:pointer;')


def index():
    
    #request.function = None
    response.title = T('More tools and abilities')
    h = CAT()
    h += show_item(T('Divided payments'),
               URL('more', 'divided_payments'),
               CAT(T('Your may  make crypto addres for send and divide an payment on it - as divideds'), BR(),BR(),
                   T('Or payouts for miners'))
               )

    return dict(h=h)


# divided_payments
def dp2():
    addrs = request.vars.pop('addrs')
    from gluon.contrib import simplejson as json
    addrs = json.loads(addrs)
    #redirect(URL())
    for addr, shares in addrs.iteritems():
        request.vars[addr] = shares

    from cp_api import make
    # выберем наш магазин служебный
    request.args.append('1')
    # зададим что входы только в валюте выхода ??
    # request.vars['curr_in'] = request.vars['curr']
    err, bill_id = make(db, request)
    print err, bill_id
    if err:
        return '%s' % err
    
    #redirect(URL('bill','show', args=[bill_id]))
    #response.js = "location.href='%s'" % URL('bill','show', args=[bill_id])
    response.js = "location.href='%s'" % 'bitcoin:1234?amo=123'
    
    return '..'

    
def dp1():
    time.sleep(1)
    l = request.vars.get('list')
    if not l:
        time.sleep(3)
        return T('List addresses and shhares is empty or wrong')
    l = l.rsplit()
    if len(l) < 4:
        time.sleep(3)
        return T('List addresses and shhares is empty or wrong')

    addrs = {}
    sum = 0.0
    for i in range( int(len(l)/2) ):
        try:
            vol = float(l[i*2+1])
        except:
            return T('In pair %s error!') % (i)
        if not vol: continue
        addrs[l[i*2]] = addrs.get(l[i*2],0) + vol
        sum += vol
    if len(addrs) < 2:
        return CAT(T('List addresses is short'),': len(addrs) < 2')
    elif len(addrs) > 200:
        return CAT(T('List addresses to long'),': len(addrs) > 200')
    elif not sum:
        return T('Total shares = 0')

    # первый адрес возьмем и проверим валююту
    addr = l[0]
    from db_common import get_currs_by_addr
    curr, xcurr, _ = get_currs_by_addr(db, addr)
    if not curr:
        time.sleep(3)
        return 'addr[1] not valid: %s' % addr

    from crypto_client import is_not_valid_addr, conn
    cc = conn(curr, xcurr)
    if not SETS.develop2 and not cc:
        return 'Connection to ' + curr.abbrev + ' wallet is lost. Try later'
    if not SETS.develop2 and is_not_valid_addr(cc, addr):
        time.sleep(3)
        return 'Address is not valid for [' + curr.abbrev + ']'

    from gluon.contrib import simplejson as json
    return CAT(T('Selected currency'),': ', B(curr.abbrev), BR(),
               T('Total shares'),': ', B(sum), BR(),
               UL(*[LI(k,': ', v, ' - ', round(100*v/sum, 6), '%' ) for k,v in addrs.iteritems()]),
               INPUT(_name='curr', _type='hidden', _value=curr.abbrev),
               TEXTAREA(_name='addrs', value=json.dumps(addrs), _hidden="hidden"),
               INPUT(_type='submit', _onclick="ajax('dp2',['curr', 'addrs'],'dp2')"),
               )


def divided_payments():
    h = CAT(
        P(T('If You need split or share or divide some payouts then use this ability'),':',
          OL([T('Set list of shared addresses'), T('Make shared bill'), T('Take pay-in address'), T('Make payment to that address')])),
        T('Input list of addresses and shares separated by spaces'),'. ',BR(),
            #T('For example'),' ','14qZ3c9WGGBZrftMUhDTnrQMzwafYwNiLt 78 14qZ3c9WGGBZrftMUhDTnrQMzwafYwNiLq 12',BR(),
            TEXTAREA(_name='list', _placeholder=T('ADDRESS1 share1 ADDRESS2 share2 ADDRESS3 share3 ...'),
                     _style='width:'+ (is_mobile and '200' or '800' ) +'px;height:240px;'),BR(),
            INPUT(_type='submit', _onclick="$('#dp1').html('<i class=\"fa fa-spin fa-spinner bbig\"></i>');ajax('dp1',['list'],'dp1')"),
            DIV(_id='dp1'),
            DIV(_id='dp2'),
        #),
        P(' '),
        )
    return dict(h=h)
