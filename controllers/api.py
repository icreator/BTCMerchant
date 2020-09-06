# coding: utf8

# сессию не писать - и не тормозить другие апросы АЯКС
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

def api_doc(k, v, controller='api', extension='json'):
    h = CAT()
    url = URL(controller, k, extension=extension!='html' and extension or None, host=True)
    if len(v)>1 and v[1]:
        h += H3('Arguments')
        ul = []
        for r in v[1]:
            descr = len(r)>1 and CAT(' - ', r[1]) or ''
            ul.append([B(r[0]), descr])
        h += UL(ul, _style='background-color:#EEE;')
    if len(v)>2 and v[2]:
        h += H3('Variables')
        ul = []
        for r in v[2]:
            descr = len(r)>1 and CAT(' - ', r[1]) or ''
            ul.append([B(r[0]), descr])
        h += UL(ul, _style='background-color:#EEE;')
            
    return DIV(
            DIV(
                DIV(H3(k),
                    controller != 'api' and CAT(T('url PATH'), ': ', B(controller)) or '',
                    _class='col-sm-3'),
                DIV(
                    len(v) >0 and DIV(v[0]) or '',
                    h,
                    _class='col-sm-9', _style='background-color:#DDD;'),
                _class='row', _style='background-color:#FDA;'),
            DIV(DIV(H4(url + (len(v)>3 and v[3] or '')), _class='col-sm-12', _style='background-color:#FFA;'), _class='row'),
            _class='row', _style='margin-bottom:15px;')

def index():
    
    #request.function = None
    response.title = T('Short API documentation')
    h = CAT()
    h += T('Request extension may be html, json, xml. Default is html.')
    h += H2(T('Common Parameters'))
    h += UL(*[LI(B(r[0]), ' - ', r[1]) for r in [
        ['SHOP_ID', T('ID of the your shop on our service')],
        ['CURR', T('abbreviation of currency. For example BTC, USD, AUD, LTC')],
        ['ADDR', T('cryptocurrency address')],
        ['BILL_ID', T('ID of the bill (invoice) on our service')],
        ['BILL_ID_SECR', CAT(T('bill_id with secret key'),'. ',T('For example'),' 1234.w3rX1daK')],
        ['ORDER_ID', T('ID of the order in your shop')],
        ['PRICE', T('The price of the order')],
        ['TX_ID', T('Transaction ID')],
        ['STATUS', CAT('NEW, FILL, SOFT, HARD, TRUE, CLOSED, EXPIRED, INVALID - ', T('see documentation'))],
        ]])
    #h += UL(li for [B('bill_id'), 'ID of the bil in our service'])
    h += H2(T('For Automatic Registrations'))
    h += api_doc('quick_reg', [CAT(T('Simple registration of your shop in our service'),'. ',
                   T('If not set shop_url then callback will not work and for check a payments need call the [check] function from API'),'. ',
                   T('It will return a SHOP_ID. If SHOP_ID < 0 then that ADDR already registered - use another ADDR for change registration parameters'),), [['ADDR']],
           [['shop_url=URL','For example http://lite.cash/bets'],
            ['icon_url=PATH','For example images/logo1.png'],
            ['note_url=PATH', 'Service will note to that path with bill_id=BILL_ID&order_id=ORDER_ID. For example callback/for_litecash?'],
            ['back_url=PATH', 'For example orders/show?&order_id='],
            ['email=EMAIL'],
            ['note_on=STATUS', CAT(T('Note on bill status:'),' SOFT|HARD|TRUE')],
            #['conv_curr','Convert all incoms to that currency'], - ignored for simple reg
            ['show_text=TEXT','Show this text for all bills'],
           ],
           '/14qZ3c9WGGBZrftMUhDTnrQMzwafYwNiLt?email=..&shop_url=http://my_shop.com/shop1&note_url=callback/for_litecash?&...',
                               ])
    h += H2(T('For make a bills (invoices)'))
    #from applications.shop.modules.cp_api import EXPIRE_MAX, EXPIRE_MINITS
    from cp_api import EXPIRE_MAX, EXPIRE_MINITS
    h += api_doc('make', [CAT(T('Making bill for your order'),'.',BR(),
                            T('It will return'),' [BILL_ID].[secret key] ', ('or [BILL_ID] if the bill is public'),'.',BR(),
                            T('Then redirect customer to bill url %s') % (URL('bill','show', host=True) + '/[BILL_ID_SECR]')),
                      [['shop_id', 'ID of yor shop in our service']],
          [
           ['price=PRICE', T('If price = 0 or not setted - make an deposit bill')],
           ['curr=CURR', T('Currency for price. Default = BTC')],
           ['conv_curr=CURR', T('Conver all payments in that CURR')],
           ['order=...', T('If order not specified then it random generated')],
           ['keep=0.001 .. 1', T('Not withdraw a payments for this bill - keep them on service for using later')],
           ['public', CAT(T('Set that bill as public'),'. ',T('For example'), ' ...curr=USD&public&price=...')],
           ['expire=INT', CAT(T('Expire bill in minutes'),'. ', 'Max = %s ' % EXPIRE_MAX,'. ',T('Default is'), ' ', EXPIRE_MINITS)],
           ['exchanging', T('This bill is for exchanging')],
           ['mess=', T('Any message')],
           ['lang=', CAT(T('Set a default languege for that bill'),'. ',T('For example'),' ...&lang=fr...')],
           ['not_convert', CAT(T('If setted then without payments convertion'),'. ',T('For example'), ' ...curr=BTC&not_convert&price=...')],
           ['curr_in=CURR', CAT(T('Ony that CURR(s) accepted'),'. ',T('For example'),' ...&curr_in=BTC&curr_in=LTC...')],
           ['curr_in_stop=CURR', CAT(T('That CURR(s) not accepted'),'. ', T('For examplle'),' ...curr_in_stop=LTC&curr_in_stop=PPC..')],
           ['back_url=PATH', T('If set override a shop [back_url] for this bill')],
           ['note_on=STATUS', T('If set override a shop [note_on] for this bill')],
           ['vol_default=FLOAT', T('Default volume for orders without PRICE')],
           ['email=EMAIL'],
           ],
          '/113?price=123&curr=USD&public&mess=HI'], 'api_bill')
    h += H2(T('For check the bill'))
    h += api_doc('check', [T('Checking bill for your order'), [['BILL_ID | BILL_ID_SECR']],
                           [
                               ['status','SOFT, FILL, HARD'],
                           ],
                           '/354?status=HARD'], 'api_bill')
    h += H2(T('For show a bills (invoices) to customer'))
    h += api_doc('show', [T('When Your obtain BILL_ID or BILL_ID_SECR you may show bill (invoice) to customer'), [['BILL_ID | BILL_ID_SECR']],
                           None, '/334.r4GsW2hs2'], 'bill', 'html')

    ### может пока ее не показывать тут??
    h += api_doc('check_txid', [T('Chech TX_ID for accept as payment if it not accepted by some error'), [['CURR'],['TX_ID']]])
    
    h += H2(T('For get a bill info'))
    h += api_doc('info', [T('Get full bill info for your order'), [['BILL_ID | BILL_ID_SECR']],
                           [
                               ['get_addrs',T('Show payments ADDR')],
                               ['all_fields',T('All fields')],
                               ['get_payouts',T('Get payouts')],
                               ['curr=CURR',T('Filter by CURR')],
                               ['from=DATETIME',T('Filter')],
                               ['till=DATETIME',T('Filter')],
                               ['start_rec=INT',T('Start from N-payment')],
                               ['recs=INT',T('Get limit payments')],
                               ['last=INT',T('Get last N payments for each CURR')],
                           ],
                           '/334.r4GsW2h4?curr=BTC&get_payouts&last=20&from=2014-01-31 20:57:02'], 'api_bill')

    h += H2(T('Other'))
    res = {
        'validate_addr': [T('Validate cryptocurrency address'), [['ADDR']]],
        'check_note': [T('Start check a note to your shop as if bill status is changed - for development and tests.'), [['BILL_ID | BILL_ID_SECR']]],
        'get_reserves': [T('Get reserves on our service. For exhange'), [['negative']]],
        'get_shops_reserves': [CAT(T('Get reserves for shops on our service'),'. ', BR(), BR(), T('It good if all = 0'))],
        'tx_info': [T('Get transaction info'), [['CURR'], ['TX_ID']]],
        'tx_senders':  [T('Get senders info for the transaction'), [['CURR'], ['TX_ID']]],
        'get_balances': [T('Get balances for the shop'), [['SHOP_ID']]],
        'bill_rates': [T('Get rates for the currency on volume'), [['CURR'], ['volume', T('For that volume')]], None, '/BTC/0.5' ],
        'curr_get_info':  ['', [['CURR']]],
    }
    res_s = sorted(res)
    for k in res_s:
        h += api_doc(k, res[k])
        
    h += H3(T('How it work'))
    h += DIV(UL([
            T('Register on service with setting [shop_url] and [note_url] - %s')
                % (URL('api', 'quick_reg', host=True) + '/[ADDR]?shop_url=...'),
            T('Make a bill by request a [make] API function and receive the BILL_ID or BILL_ID_SECR - %s ')
                % (URL('api_bill', 'make', host=True) + '/[SHOP_ID]?price=...'),
            T('Show to customer a bill by call a [show] url - %s')
                % (URL('bill', 'show', host=True) + '/[BILL_ID]'),
            T('Service will notify to [shop_url]/[note_url] when customer will pay that bill'),
            T('Check a status of a bill by call a [check] API function, when our service notify your shop - %s')
                % (URL('api_bill', 'check', host=True) + '/[BILL_ID]'),
            T('Set a order status to "payed" if a status of the bill is SOFT or HARD or CLOSED - we recommend waiting a HARD status'),
                ]),
        _class='row')

    return dict(h=h)

def curr_get_info():
    import time
    time.sleep(1)

    curr_abbrev = request.args(0)
    if not curr_abbrev:
        return {"error": "empty curr - example: curr_get_info/btc" }
    curr_abbrev = curr_abbrev.upper()
    #from applications.shop.modules.db_common import get_currs_by_abbrev
    from db_common import get_currs_by_abbrev
    curr,xcurr,e = get_currs_by_abbrev(db, curr_abbrev)
    if not xcurr:
        return {"error": "invalid curr: " + curr_abbrev }
    from crypto_client import conn
    conn = conn(curr, xcurr)
    if not conn:
        return {'error': 'Connection to ' + curr_abbrev + ' wallet is lost. Try later'}
    res = conn.getinfo()
    return res

def quick_reg():
    #url = request.vars['shop_url']
    #if url and url in ['localhost', '127.0.0.1']:
    #    time.sleep(1)
    #    return 'You can\'t use [localhost] !'
    return register_simple()

def register_simple():
    time.sleep(1)
    addr = request.args(0)
    if not addr or len(addr) < 30:
        time.sleep(3)
        return 'len(addr) < 30'
    from db_common import get_currs_by_addr
    curr, xcurr, _ = get_currs_by_addr(db, addr)
    if not curr:
        time.sleep(3)
        return 'addr[1] not valid'

    from crypto_client import is_not_valid_addr, conn
    cc = conn(curr, xcurr)
    if not cc:
        return 'Connection to ' + curr.abbrev + ' wallet is lost. Try later'
    if is_not_valid_addr(cc, addr):
        time.sleep(3)
        return 'Address is not valid for [' + curr.abbrev + ']'

    url = request.vars['shop_url']
    if url and url in ['http://localhost', 'http://127.0.0.1', 'https://localhost', 'https://127.0.0.1']:
        time.sleep(1)
        return 'cant use [localhost] !'

    shop = db(db.shops.name==addr).select().first()
    if shop:
        return -shop.id # already registered

    # жестко зададим валюту конвертации
    from shops_lib import make_simple_shop
    shop = make_simple_shop(db, addr, request.vars, True, curr, xcurr)
    if not shop:
        time.sleep(2)
        return 'Error on making registration. Please connect to support'

    return shop.id


# проверить статус заказа
# для продолженных заказв параметр status =
# # http://127.0.0.1:8000/shop/api/check_note.json/278
def check_note():
    time.sleep(3)
    from orders_lib import check_args
    err, _, _, shop_order = check_args(db, request)
    if err or not shop_order:
        return err or 'biil not exist'
    shop = db.shops[shop_order.shop_id]
    if not shop.url: return 'shop url empty'
    from shops_lib import try_make_note_url2
    url_path = try_make_note_url2(db, shop, shop_order, None)
    res = url_path and shops_lib.notify_one_url(db, shop, shop_order)
    return { 'result_note_url': shop.url + (url_path or 'None'), 'response_status': res and res.status, 'response_text': res and res.read() }


########################################################################
########################################################################
def get_reserves():
    time.sleep(1)
    bals = dict()
    from db_common import get_reserve
    negative = request.args(0)
    for curr in db(db.currs).select():
        if not curr.used: continue
        b = get_reserve( curr, negative )
        bals[curr.abbrev] = float(b)

    return bals

def get_shops_reserves():
    time.sleep(1)
    bals = dict()
    from db_common import get_shops_reserve
    for curr in db(db.currs).select():
        if not curr.used: continue
        b = get_shops_reserve( curr )
        bals[curr.abbrev] = float(b)

    return bals


# api/tx_info.json/BTC/ee4ddc65d5e3bf133922cbdd9d616f89fc9b6ed11abbe9a040dac60eb260df23
# api/tx_info.html/BTC/ee4ddc65d5e3bf133922cbdd9d616f89fc9b6ed11abbe9a040dac60eb260df23
def tx_info():
    time.sleep(1)

    txid = request.args(1)
    if not txid:
        return {'error':"need txid: /tx_info.json/[curr]/[txid]"}
    curr_abbrev = request.args(0).upper()
    from db_common import get_currs_by_abbrev
    curr,xcurr,e = get_currs_by_abbrev(db, curr_abbrev)
    if not xcurr:
        return {"error": "invalid curr: " + curr_abbrev }
    from crypto_client import conn
    conn = conn(curr, xcurr)
    if not conn:
        return {'error': 'Connection to ' + curr_abbrev + ' wallet is lost. Try later'}
    from crypto_client import get_tx_info
    res = get_tx_info(conn, txid, request.vars)
    return res

# api/tx_senders/BTC/ee4ddc65d5e3bf133922cbdd9d616f89fc9b6ed11abbe9a040dac60eb260df23
def tx_senders():
    time.sleep(1)
    txid = request.args(1)
    if not txid:
        #raise HTTP(501, {"error": "empty pars"})
        return {'error':"need txid: /tx_senders.json/[curr]/[txid]"}
    curr_abbrev = request.args(0).upper()
    from db_common import get_currs_by_abbrev
    curr,xcurr,e = get_currs_by_abbrev(db, curr_abbrev)
    if not xcurr:
        return {"error": "invalid curr"}
    from crypto_client import conn
    conn = conn(curr, xcurr)
    if not conn:
        return {"error": "not connected to wallet"}
    res = dict(result=crypto_client.sender_addrs(conn, txid))
    return res


# http://127.0.0.1:8000/shop/api/validate_addr.json/14qZ3c9WGGBZrftMUhDTnrQMzwafYwNiLt
def validate_addr():
    time.sleep(1)
    addr = len(request.args)>0 and request.args[0] or request.vars.get('addr')
    if not addr:
        return {'error':"need addr: /validate_addr.json/[addr]"}
    from db_common import get_currs_by_addr
    curr, xcurr, _ = get_currs_by_addr(db, addr)
    if not xcurr:
        return {"error": "invalid curr"}
    from crypto_client import conn
    conn = conn(curr, xcurr)
    if not conn:
        return {"error": "not connected to wallet [%s]" % curr.abbrev}
    valid = conn.validateaddress(addr)
    if not valid.get('isvalid'):
        return {"error": "invalid for [%s]" % curr.abbrev}
    return { 'curr': curr.abbrev, 'ismine': valid.get('ismine') }


##https://7pay.in/ipay/to_shop/get_balances/[shop_id]
# http://127.0.0.1:8000/shop/api/get_balances.json/2
# http://127.0.0.1:8000/shop/api/get_balances.html/2
def get_balances():
    time.sleep(1)
    if not request.args or len(request.args)==0:
        return { "error": "args is empty" }

    shop_id = request.args[0]
    if not shop_id:
        time.sleep(5)
        return { "error": "shop_id empty"}

    if len(shop_id)>30:
        shop = db(db.shops.name == shop_id).select().first()
        shop_id = shop and shop.id
        if not shop_id:
            time.sleep(5)
            return { "error": "shop [%s] not found" % request.args[0]}
    else:
        try:
            shop_id = int(shop_id)
        except:
            time.sleep(5)
            return { "error": "shop_id invalid"}

    if not db.shops[shop_id]:
        time.sleep(5)
        return { "error": "shop [%s] not found" % request.args[0]}

    bals = {}
    for rec in db(db.shops_balances.shop_id == shop_id).select():
        curr = db.currs[rec.curr_id]
        bals[curr.abbrev] = round(float(rec.bal),9)
    return bals

# api/bill_rates/BTC/vol
# по какому курсу входные валюты зачтем
def bill_rates():
    time.sleep(1)
    if len(request.args) == 0:
        mess = 'ERROR: - use api/rates/BTC'
        return mess
    curr_in = db(db.currs.abbrev==request.args(0).upper()).select().first()
    if not curr_in: return 'curr not found'

    from rates_lib import get_best_rates
    best_rates = get_best_rates(db, curr_in, True)
    res = {}
    for v in best_rates:
        if v == curr_in.id: continue
        res[db.currs[v].abbrev] = best_rates[v]
    return res
