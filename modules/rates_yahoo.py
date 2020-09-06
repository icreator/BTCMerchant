# coding: utf8

EXCH_NAME = 'Yahoo'

import decimal

import rates_lib
'''
Yahoo - тут маржа мизер поэтому вводим базовый % большой - 1-2% и для 100 долларов обмен делаем
http://query.yahooapis.com/v1/public/yql?q=select * from yahoo.finance.xchange where pair in ("USDEUR", "USDJPY", "USDBGN", "USDCZK", "USDDKK", "USDGBP", "USDHUF", "USDLTL", "USDLVL", "USDPLN", "USDRON", "USDSEK", "USDCHF", "USDNOK", "USDHRK", "USDRUB", "USDTRY", "USDAUD", "USDBRL", "USDCAD", "USDCNY", "USDHKD", "USDIDR", "USDILS", "USDINR", "USDKRW", "USDMXN", "USDMYR", "USDNZD", "USDPHP", "USDSGD", "USDTHB", "USDZAR", "USDISK")&env=store://datatables.org/alltableswithkeys
'''

# все относительно доллара
def get_currs(currs):
    curr_in='USD'
    pars_enc = 'q=select * from yahoo.finance.xchange where pair in ('
    for code in currs:
        pars_enc += '"%s%s",' % (curr_in, code)
    pars_enc = pars_enc[:-1]
    
    pars_enc += ')&env=store://datatables.org/alltableswithkeys&format=json'
    #return None, pars_enc
    import urllib2
    req = urllib2.Request('http://query.yahooapis.com/v1/public/yql',
           pars_enc,
           #headers,
           )
    #return None, '%s' % req
    page = urllib2.urlopen(req)
    res = page.read()
    #print res
    import gluon.contrib.simplejson as sj
    res = sj.loads(res)
    #print res
    currs = res.get('query')
    currs = currs and currs.get('results')
    currs = currs and currs.get('rate')
    if not currs:
        print res
        return res, None
    #print currs
    res = {}
    # если на входе одна пара то на выходе нет массива
    if type(currs) != type([]):
        currs = [currs]
    for curr in currs:
        if curr['Name'] == 'N/A':
            continue
        code = curr['id'][3:]
        rate = 1/ float(curr['Rate'] or -1)
        #rate = 1/ float(curr['Ask'] or -1)
        dd = curr['Date']
        tt = curr['Time']
        res[code] = rate
    return None, res

# все относительно доллара чтобы не путаться
# curr_in - если уже найдена была ранее - то не добавляем
def set_curr(db, abbrev, curr_in = None):
    curr = curr_in or db(db.currs.abbrev==abbrev).select().first()

    curr_out = 'USD'
    err, rates = get_currs([ abbrev ])
    if err: return err, None
    
    # такая валюта найдена
    rate = rates.get(abbrev)
    if not rate:
        return { 'error': 'currency not found as fiat' }, None
    
    err, res = rates_lib.set_rate_base_ecurr(db, abbrev, curr, rate, 'USD', EXCH_NAME, 1)

    return err, res
