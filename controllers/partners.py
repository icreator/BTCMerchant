# coding: utf8
# попробовать что-либо вида

response.title=T("Заработаем Вместе!")
response.big_logo2=True
response.logo2 = IMG(_src=URL('static','images/slide2.png'), _width=198)


def make_p_url(id, deal_name, cod):
    if deal_name == 'phone +7':
        return '<a href=%s>%s</a>' % (URL('to_phone','index',args=[cod], scheme=True, host=True),
                                  T('Получи подарок пополнив сотовый телефон!'))

    return '<a href=%s>%s</a>' % (URL('more','to_pay',args=[id, cod], scheme=True, host=True),
                                  T('Получи подарок в %s') % deal_name)

def index():
    #print request.post_vars
    addr = request.post_vars.wallet
    if not addr or len(addr)<2:
        return dict(mess = '', cod=None)
    if addr and len(addr)<30:
        return dict(mess = T('Неверый адресс'), cod=None)
        
    #print addr
    deal_acc_addr = db(db.deal_acc_addrs.addr == addr).select().first()
    if not deal_acc_addr: return dict(mess="not found deal_acc_addr", cod=None)
    
    deal_acc = db.deal_accs[deal_acc_addr.deal_acc_id]
    if not deal_acc: return dict(mess="not found deal_acc", cod=None)
    
    deal = db.deals[deal_acc.deal_id]
    if not deal: return dict(mess="not found deal", cod=None)
    if deal.not_gifted:
        mess = T('Это дело [%s] не может быть использовано для сотрудничества.') % deal.name
        return dict(mess = mess, cod=None)
    
    mess = T('Для дела [%s] и аккаунта [%s]') % (deal.name, deal_acc.acc)
    response._deal_name = deal.name
    response._acc = deal_acc.acc
    cod = deal_acc.partner
    if cod and len(cod) >4:
        #mess = "++ %s" % mess
        response._partner_sum = deal_acc.partner_sum
        response._partner_url = make_p_url(deal.id, deal.name, cod)
        response._partner_count = db(db.deal_accs.gift==cod).count()
        return dict(mess = mess, cod=cod)
    
    if not deal_acc.payed or deal_acc.payed < 100:
        u = A(deal.name, _href=URL('more','to_pay', args=[deal.id]))
        return dict(mess = XML(T('Вы не можете начать сотрудничество пока сами не совершите платеж хотя бы на 100 рублей через наш сервис по этому делу [%s]. Ваш сумарный платеж %s рублей.') % (u, deal_acc.payed or 0)), cod=None)

    for i in range(1, len(addr) - 11):
        cod = addr[i:i+10]
        #print cod
        deal_acc_is = db(db.deal_accs.partner==cod).select().first()
        if not deal_acc_is:
            deal_acc.partner = cod
            # партнеры не получают подарков, поэтому сбросим подарок
            deal_acc.gift_amount = 0 # None
            deal_acc.gift_pick = 0 # None
            deal_acc.gift = None
            deal_acc.update_record()
            response._partner_url = make_p_url(deal.id, deal.name, cod)
            return dict(mess = mess, cod = deal_acc.partner)
    
    return dict(mess=T('Что-то не так'), cod=None)
