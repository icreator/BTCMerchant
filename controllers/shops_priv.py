# coding: utf8
import common
# запустим сразу защиту от внешних вызов
#print request.function
#if request.function not in ['list', 'download'] and common.not_is_local(): raise HTTP(200, T('ERROR'))
if common.not_is_local(): raise HTTP(200, T('ERROR'))

import datetime
import json

import db_common
import db_client


def log(l2, mess):
    m = 'shops_lib'
    print m, mess
    db.logs.insert(label123456789 = m, label1234567890=l2, mess='%s' % mess)
def log_commit(db, l2, mess='>'):
    log(db, l2, mess)
    db.commit()

    
def list():
    h = CAT()
    for r in db(db.shops).select():
        
        h += DIV(
            A(r.id, _href=URL('appadmin','update', args=['db','shops',r.id]), _target='_blank'),'. ',
            '--' if r.not_used else '',
            B(r.uses),' ',
            A(r.simple_curr and (r.url or '???') or r.name, _href=r.url, _target='_blank') if r.url else r.name,
            ' ', r.email,' ', r.descr,
            _class='row')
    
    return dict(h=h)

def resum_currs_deposit():
    import crypto_client
    sum = 0
    for curr in db(db.currs).select():
        sum1 = db.shops_balances.bal.sum()
        sum2 = db(db.shops_balances.curr_id==curr.id).select(sum1).first()[sum1]
        #print  curr.abbrev, summ2
        curr.update_record(shops_deposit = sum2)
        xcurr = db(db.xcurrs.curr_id==curr.id).select().first()
        if xcurr:
            try:
                cn = crypto_client.conn(curr, xcurr)
                #print cn
                if cn:
                    bal = cn.getbalance()
                    print curr.abbev, bal
            except:
                pass
        
        
#############################################
def show(r):
    print r
def edit_bals():
    res=[]
    '''
    res.append( SQLFORM(ShBals, fields=['shop_id'], formstyle='divs',
              )
        )
    if res[0].process().accepted:
        res.append( SQLFORM.grid(ShBals, formstyle='divs') )
        pass
    '''
    res.append( SQLFORM.grid(ShBals,
         selectable = [('Change ballance', lambda r: show(r)),('button label2',lambda r:  r)],
         formstyle='divs') )
    rid = request.args(0)
    if rid:
        res[0].buttons.append(BUTTON())
    return locals()

# шлем рассылку в скрытых копиях
def send_email_to_descr(to_addrs, subj, mess=None, rec=None, templ=None):
    if not_is_local(): raise HTTP(404, T('ERROR 0131'))
    from gluon.tools import Mail
    mail = Mail()
    #mail.settings.server = 'smtp.yandex.ru' #:25'
    mail.settings.server = 'smtp.sendgrid.net'
    mail.settings.sender = 'support@cryptoPay.in'
    #mail.settings.login = 'support@7pay.in:huliuli'
    mail.settings.login = 'azure_90ebc94457b0e6a1c4c920993753f5a6@azure.com:7xirv1rc'
    mess = mess or ''
    if rec and templ:
        context = dict( rec = rec )
        #mess = response.render('add_shop_mail.html', context)
        mess = response.render(templ, context)
    #print mess
    #to_addrs = ['kentrt@yandex.ru','icreator@mail.ru']
    mail.send(
          #to=to_addrs[0],
          to=to_addrs,
          #cc=len(to_addrs)>1 and to_addrs[1:] or None, - как спам коипии делает (
          #bcc=len(to_addrs)>1 and to_addrs[1:] or None,
          subject=subj,
          message=mess)

def mail_to_clients1():
    if not_is_local(): raise HTTP(404, T('ERROR 0131'))
    subj = 'Новости от биллинга cryptoPay.in - 2'
    mess = '''
    Здравствуйте!
    
    Появился модуль (плагин) биллинга поатежей для магазинов, созданных на PrestaShop http://cryptopay.in/shop/default/plugins
    Подключение свободное и бесплатное. Просьба тех кто хочет установить на свой сайт этот плагин, откликнуться.
    
    С Уважением, Ермолаев Дмитрий
    '''
    mess = mess + '%s.' % A('cryptoPay.in', _href='http://cryptoPay.in')
    #send_email_to_descr('icreator@mail.ru',subj,mess)
    return mess
    to_addrs = []
    for r in db(db.startup).select():
        to_addrs.append(r.email)
        if len( to_addrs ) > 5:
            send_email_to_descr(to_addrs, subj, mess)
            to_addrs = []
    if len(to_addrs)>0: send_email_to_descr(to_addrs, subj, mess)
    
def mail_to_polza1():
    if not_is_local(): raise HTTP(404, T('ERROR 0131'))
    subj = 'cryptoPay.in - СТАРТАП: сообщение 7'
    return 'stopped'
    mess = '''
    Здравствуйте!
    
    И так нас зарегистрировали. Название выбрано нейтральное что бы не привлекать внимание на начальных этапах и при регистрации:
    Инновационное Постребительское Общество "Польза"
    
    Открыт расчетный счет в СберБанке, теперь можно вносить взносы.
    
    Запущен сайт ipo-polza.ru
    На нем можно регистрироваться и оплачивать вступительные взносы
    
    Созданы программы:
    1. "получи 500 рублей приведя своих друзей"
    2. вклад 37,77% за 777 дней (или 18% годовых)
    
    Для получения новостей, подключайтесь в социальной сети google+ к пользователю ipo.polza@gmail.com

    
    С Уважением, Дмитрий Ермолаев
    http://ipo-polza.ru
'''
    #mess = mess + '%s.' % A('cryptoPay.in Стартап', _href='http://cryptopay.in/shop/default/startup')
    #send_email_to_descr('icreator@mail.ru',subj,mess)
    to_addrs = []
    if True:
        for r in db(db.startup).select():
            to_addrs.append(r.email)
            if len( to_addrs ) > 5:
                send_email_to_descr(to_addrs, subj, mess)
                to_addrs = []
        if len (to_addrs) > 0: send_email_to_descr(to_addrs, subj, mess)
    else:
        send_email_to_descr(['icreator@mail.ru'], subj, mess)

    return 'sended'
