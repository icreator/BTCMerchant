#!/usr/bin/env python
# coding: utf8
import datetime

import logging
logger = logging.getLogger("web2py.app.shop")
logger.setLevel(logging.DEBUG)

def lg(mess):
    logging.error( u'TEST1' )
    logger.error( u'TEST2' )

#log =logging.Logger()
#log.debug
ROUND_SATOSHI = 8
def rnd_8(v):
    return round(float(v or 0), ROUND_SATOSHI)

from gluon import *
def ip(): return current.request.client

#import urllib
import trans
def uri_make_url(name, addr, pars_in):

    #pars = urllib.urlencode(pars_in)
    ppp = "?"
    for k,v in pars_in.iteritems():
        if len(ppp)==1:
            ppp = ppp + '%s=%s' % (k,v)
        else:
            ppp = ppp + '&%s=%s' % (k,v)
    if name=='copperlark': ppp=''
    ppp = ppp.decode('utf8')
    ppp = ppp.encode('trans')

    return name + ":" + addr + ppp

def uri_make(name, addr, pars_in, label_in=None):
    return A(XML('<button class="uri">%s</button>' % 
                 (label_in or current.T('ОПЛАТИТЬ'))), _class='btn_uri', _href=uri_make_url(name, addr, pars_in))


def get_host(url):
    if url[-1:] == '/': url = url[:-1]
    if url[0:8] == 'https://': url = url[8:]
    elif url[0:7] == 'http://': url = url[7:]
    return url

def page_stats(db,view):
    return
    ss = db(db.site_stats.page==view).select().first()
    if not ss:
        id = db.site_stats.insert(page=view, loads=1)
        return 1
    ss.loads = ss.loads + 1
    ss.update_record()
    # вызов там на страницах автоматом этот db.commit()
    print view, ss.loads, ip()
    return ss.loads

def last_year():
    td = datetime.date.today()
    m = td.month
    y = td.year
    if m == 1: return y-1
    return y
def last_year2():
    y = "%s" % last_year()
    return y[-2:]
def last_month():
    td = datetime.date.today()
    m = td.month
    y = td.year
    if m == 1: return 12
    return m-1

def not_is_local():
    http_host = current.request.env.http_host.split(':')[0]
    remote_addr = current.request.env.remote_addr
    try:
        hosts = (http_host, socket.gethostname(),
                 socket.gethostbyname(http_host),
                 '::1', '127.0.0.1', '::ffff:127.0.0.1')
    except:
        hosts = (http_host, )

    if (remote_addr not in hosts) and (remote_addr != "127.0.0.1"):
        return True
