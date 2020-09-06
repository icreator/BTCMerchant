# coding: utf8
from gluon import current
T = current.T

from datetime import datetime, timedelta
from decimal import Decimal

from db_common import *
import crypto_client
import rates_lib

import trans
# с переворотом кирилицы в латиницу
def make_x_acc(deal, acc, curr_out_abbrev, format='sh [%s] [%s] [%s]'):
    # это имя аккаунта в моем кошельке какое будет
    ppp = format % (deal and deal.name or '', acc, curr_out_abbrev)
    ppp = ppp.decode('utf8')
    ppp = ppp.encode('trans')
    return ppp
def make_x_acc_label(deal, acc, curr_out_abbrev,  format='cryptoPay.in -> [%s] [%s] [%s]'):
    # это имя аккаунта в кошельке клиента - чтобы ему было понятней
    ppp =  format % (deal and deal.name or '', acc, curr_out_abbrev)
    ppp = ppp.decode('utf8')
    ppp = ppp.encode('trans')
    return ppp

# old def get_deal_acc_id_for_deal_and_acc(db, deal, acc, acurr):
# создаем заказ длля данного дела с заданной суммой заказа
def get_deal_acc_id(db, deal, acc, curr_out, price=None):
    if not acc or len(acc)<3: return
    # найдем аккаунт для данного дела или создадим
    # если пустой аккаунт в записи то его почемуто находит ((
    deal_acc = None
    for rec in db((db.deal_accs.deal_id==deal.id) # для данного дела
            & (db.deal_accs.acc==acc) # есть такой аккаунт
            ).select():
        if len(rec.acc)<3: continue
        deal_acc = rec
        break

    if deal_acc:
        deal_acc_id = deal_acc.id
    else:
        deal_acc_id = db.deal_accs.insert(deal_id = deal.id, acc = acc, curr_id = curr_out.id, price = price)
    return deal_acc_id

def get_shop_order_addr_for_xcurr(db, shop_order_id, curr, xcurr, order_id_label):
    # найдем адрес крипты для данногоо аккаунта дела или создадим
    shop_order_addr = db((db.shop_order_addrs.shop_order_id==shop_order_id)
        & (db.shop_order_addrs.xcurr_id==xcurr.id)
        ).select().first()
    if not shop_order_addr:
        conn = crypto_client.conn(curr, xcurr)
        if not conn: return
        # http://docs.python.org/2/library/codecs.html?highlight=decoding
        ### после trans - не надо! x_acc_label = order_id_label.decode('utf8')
        #x_acc_label = x_acc_label.encode('koi8_r') # 'iso8859_5') # 'cp866') # 'cp1251') #'cp855')
        #x_acc_label = x_acc_label.decode('cp855')
        x_acc_label = order_id_label
        print 'GET new addr for',x_acc_label
        ## тут нельзя по метке брать адрес - так как метка может быть от старого счета для заказа с тем же номером
        ## addr = crypto_client.get_xaddress_by_label(conn, x_acc_label)
        ## делаем по номеру счета адрес
        # TODO - надо сделать проверку в кошельке - может там такого адреса нет который есть в ДБ
        # может новый кошель создан а база у нас старая с адресами - надо новый адрес сгенерить!!!
        addr = crypto_client.get_xaddress_by_label(conn, '%s' % shop_order_id)
        
        if not addr: return
        else:
            id = db.shop_order_addrs.insert(
                  shop_order_id = shop_order_id,
                  xcurr_id=xcurr.id,
                  addr = addr)
            shop_order_addr = db.shop_order_addrs[id]
    return shop_order_addr

######################################################


####################################################################
# для выбора крипты в формах оплаты для данного дела
####################################################################
def curr_free_bal(curr):
    bal_out = Decimal(curr.balance) - Decimal(curr.deposit) - Decimal(curr.shops_deposit) - Decimal(curr.fee_out)
    if bal_out < 0: bal_out = 0
    return bal_out

# not_used - список запрещенных валют для клиентов или магазинов
# only_used - список только используемых валют
def get_xcurrs_for_shop(db, volume_out, curr_out, shop, not_used=None, only_used=None):
    curr_out_id = curr_out.id

    pairs = []

    dealer_id = None
    s_b = True
    d_e = None
    # теперь по всем криптам пройдемся и если нет в парах то
    # значит запрет в форме сделаем
    for rec_in in db((db.currs.used==True) 
                     & (db.xcurrs.curr_id==db.currs.id)).select(orderby='currs.name'):
        curr_in = rec_in.currs
        if not_used and curr_in.abbrev in not_used: continue
        if only_used and curr_in.abbrev not in only_used: continue
        disabled = None
        exchg_lst = ''

        if curr_in.id == curr_out.id:
            pr_b = 1.0
        else:
            #acurr_in = db(db.acurrs.xcurr_id==xcurr_in.id).select().first()
            # берем в расчет только недавние цены
            pr_b, pr_s, pr_avg = rates_lib.get_average_rate_bsa(db, curr_in.id, curr_out_id)
            #if curr_in.abbrev == 'CLR': print curr_in.name, pr_b, pr_s, pr_avg
            pp = None
            if pr_b:
                volume_in = volume_out / float(pr_b)
                #if curr_in.abbrev == 'CLR': print volume_in, volume_out, pr_b
                # тут уже с учетом комиссии биржи на фиат
                # get_best_price_for_volume(db, id1, id2, vol, expired, s_b=None, dealer_id=None, d_e=None):
                ao_, ro_, pr_b = rates_lib.get_rate(db, curr_in, curr_out, volume_in)
                #if curr_in.abbrev == 'CLR': print 'pr_b', pr_b

            if not pr_b:
                pr_b = -1
                disabled = True
            else:
                for p in pp or []:
                    exch = db.exchgs[p['exchg_id']]
                    exchg_lst = exchg_lst + exch.name + ' '

        #currs_stats = db((db.currs_stats.curr_id==curr_in.id)
        #        & (db.currs_stats.shop_id==shop.id)).select().first()

        pairs.append({ 'id':curr_in.id, 'price': pr_b,
                  'name': curr_in.name, 'abbrev': curr_in.abbrev, 'icon': curr_in.icon,
                  'exch': exchg_lst,
                  'expired': disabled,
                  'name_out': curr_out.abbrev,
                  #'used': currs_stats and currs_stats.count or 0,
                  'curr_id': curr_in.id, # для того чтобы по 2му разу не брало
                  #'bal': curr_in.balance,
                  #'bal_out': curr_free_bal(curr_in) #  сколько можно продать
                })

    return pairs


# тут надо все таксы учесть
def get_fees_for_out(db, deal, dealer_deal, curr_in, curr_out, volume_out, rate, pairs, taxs, fee_ed):
    info = []
    if curr_in.id == curr_out.id:
        return volume_out, rate, info
    # здесь уже в курсе учтены такса биржи и такса вывода с биржи на диллера
    # теперь добавим таксу диллера для этого дела и наши таксы все
    vol = float(volume_out)
    # добавим наш оброк на дело
    fee = float(deal and deal.fee or 0)
    if fee >0:
        vol = vol + fee
        info.append(T('+ плата сервису %s[%s] по делу "%s". ') % (fee, curr_out.abbrev, deal.name))
    # добавим наш оброк на вывод
    fee = float(curr_out.fee_out or 0)
    if fee >0:
        vol = vol + fee
        info.append(T('+ плата сервису %s[%s]. ') % (fee, curr_out.abbrev))
    # добавим таксу диллера за это дело
    tax = float(dealer_deal and dealer_deal.tax or 0)
    if tax >0:
        vol = vol * (1.0 + tax*0.01)
        info.append(('+ %s' % tax) + '% ' + T('такса диллера электронных денег за перевод "%s". ') % (deal.name))
    # добавим таксу нашу на вывод валюты
    tax = float(curr_out.tax_out or 0)
    if tax >0:
        vol = vol * (1.0 + tax*0.01)
        info.append(('+ %s' % tax) + '% ' + T('такса сервиса за вывод валюты [%s]. ') % curr_out.abbrev)

    # теперь посмотрим сколько надо входа:
    vol_in = vol / rate
    info.append(T('Рачетный курс: %s с учетом комиссии бирж') % rate)
    #print pairs, taxs
    if taxs and len(taxs)>0:
        info.append(T(': {'))
        i=0
        for tax in taxs:
            pair = pairs[i]
            curr_out = db.currs[pair['curr2_id']]
            i=i+1
            for exchg_name, vol in tax.iteritems():
                ss = '%s ->[%s]: %s' % (exchg_name, curr_out.abbrev, vol*100)
                info.append(ss + '%; ')
        info.append(' ')
        info.append('} и')

    if fee_ed and fee_ed!=0:
        # тут значение не в процентах, поэтому умножим на 100
        info.append(T(' вывода с биржи %s: %s') % (exchg_name, fee_ed*100) + '%. ')


    # тепеь добавим таксы на вход - в обратном порядке от выхода накрутки
    tax = float(curr_in.tax_in or 0)
    if tax >0:
        vol_in = vol_in * (1.0 + tax*0.01)
        info.append(('+ такса сервиса %s' % tax) + '% ' + T('от входа [%s]. ') % (curr_in.abbrev))
    # это такса за создание заказа и столбление курса в заказе
    fee = float(curr_in.fee_in or 0)
    if fee >0:
        vol_in = vol_in + fee
        info.append(T('+ плата за заказ %s[%s]. ') % (fee, curr_in.abbrev))

    volume_in = round(vol_in, 8)
    print volume_in, volume_out

    # пересчитаем курс тогда
    rate_out = round(volume_out / volume_in, 8)
    return volume_in, rate_out, info


# взять все оброки и таксы при расчете от входящего количества монет
# тут уже учтено комиссия биржы и комиссия вывода
def use_fees_for_in(db, deal, dealer_deal, curr_in, curr_out, vol_in, rate, mess_in=None):
    mess = mess_in or ''
    if curr_in.id == curr_out.id:
        return vol_in, mess
    vol_in = float(vol_in)
    ''' для свободных входов - без закзаз - они идут по входам - НЕ БЕРЕМ эту таксу
    # это такса за создание заказа и столбление курса в заказе
    fee = float(curr_in.fee_in or 0)
    if fee >0:
        vol_in = vol_in + fee
    print deal
    print dealer_deal
    print curr_in
    print curr_out
    '''
    # тепеь добавим таксы на вход - в обратном порядке от выхода накрутки
    tax = float(curr_in.tax_in or 0)
    if tax >0:
        vol_in = vol_in * (1.0 - tax*0.01)
        mess = mess + T('Комиссия на вход: %s') % tax + '% . '

    # теперь посмотрим сколько получили выхода:
    vol = vol_in * rate
    mess = mess + T('(прямой курс: x%s, обратный курс: /%s ). ') % (rate, 1/rate)

    # добавим таксу нашу на вывод валюты
    tax = float(curr_out.tax_out or 0)
    if tax >0:
        vol = vol * (1.0 - tax*0.01)
        mess = mess + T('Комиссия на выход: %s') % tax + '% . '

    # добавим таксу диллера за это дело
    tax = float(dealer_deal and dealer_deal.tax or 0)
    if tax >0:
        vol = vol * (1.0 - tax*0.01)
        mess = mess + T('Комиссия диллера: %s') % tax + '% . '

    # добавим наш оброк на вывод
    fee = float(curr_out.fee_out or 0)
    if fee >0:
        vol = vol - fee
        mess = mess + T('Плата за вывод: %s [%s]. ') % (fee, curr_out.abbrev)

    # добавим наш оброк на дело
    fee = float(deal and deal.fee or 0)
    if fee >0:
        vol = vol - fee
        mess = mess + T('Плата по делу: %s. ') % fee

    vol_out = vol

    return vol_out, mess
