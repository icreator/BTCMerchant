# coding: utf8

EXCH_NAME = 'PayPal'

import datetime
import decimal

import rates_lib

###############################################################
### ВНИМАНИЕ!!! - тут сколько получишт валюты на выходе с включенным уже %% пайпала -который 2-5%
### а нам нужен обратный курс с обратными процентами чтобы посмотреть сколько надо долларов заплатить чтобы получитьтакое кол-во тубриков местных
### поэтому лучше использовать Yahoo - там без %% вообще
### и поэтому тут %% для обменника 5 задаем
def get_currs(currs, curr_out='USD', amo = 10000):
    headers = {
		'X-PAYPAL-SECURITY-USERID': 'icreator_api1.mail.ru',
		'X-PAYPAL-SECURITY-PASSWORD': 'QCFV89QVMEZEWVN7',
		'X-PAYPAL-SECURITY-SIGNATURE': 'AcAlkfEgqecaI7ag4dS4t08-dC4qA.QSQARya9k3hgP6zu37OJFGX.rV',
		'X-PAYPAL-APPLICATION-ID': 'APP-33J964988G981414D',
		'X-PAYPAL-REQUEST-DATA-FORMAT': 'NV',
		'X-PAYPAL-RESPONSE-DATA-FORMAT': 'JSON'
	}
    pars_enc = 'requestEnvelope.errorLanguage=en_US&method=ConvertCurrency&requestEnvelope.detailLevel=ReturnAll&countryCode=US'
    pars_enc += '&convertToCurrencyList.currencyCode=%s' % curr_out
    i = 0
    for code in currs:
        pars_enc += '&baseAmountList.currency(%s).code=%s&baseAmountList.currency(%s).amount=%s' % (i, code, i, amo)
        i +=1
    
    import urllib2
    req = urllib2.Request('https://svcs.paypal.com/AdaptivePayments/ConvertCurrency',
           pars_enc,
           headers,
           )
    page = urllib2.urlopen(req)
    res = page.read()
    import gluon.contrib.simplejson as sj
    res = sj.loads(res)
    currs = res.get('estimatedAmountTable')
    currs = currs and currs.get('currencyConversionList')
    if currs:
        res = {}
        for curr in currs:
            code = curr['baseAmount']['code']
            amo_in = curr['baseAmount']['amount']
            amo_out = curr['currencyList']['currency'][0]['amount']
            #res[code] = float(amo_in or 0) / float(amo_out or -1)
            res[code] = float(amo_out or 0) / float(amo_in or -1)
        return None, res
        #return None, currs
    else:
        return res, None

def set_curr(db, abbrev):

    ### так как ПэйПэл очень сильно округляет то для слабых валют нужно задать большой обмен
    price = 1000
    rate = 0
    while True:
        err, rates = get_currs({ abbrev: price })
        if err: return err, None
        # такая валюта найдена
        rate = rates[abbrev]
        print rate, price, price*rate
        if price*rate > 30: break
        # иначе увеличим объем обмена
        price *= 100
    
    curr = db(db.currs.abbrev==abbrev).select().first()
    
    err, res = rates_lib.set_rate_base_ecurr(db, abbrev, curr, rate, 'USD', EXCH_NAME, 5)

    return err, res
