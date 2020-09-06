# coding: utf8


def list():
    l = [TR(TD(B(T('Иконка')), _class='center'),
            TD(B(T('Польз'), _class='center')), TD(B(T('Описание')), _class='center'), _class='oll3a')]
    #for r in db(db.shops.not_listed != True ).select( orderby=~db.shops.uses|db.shops.name ):
    for r in db(((db.shops.not_listed != True)
                | (db.shops.not_listed == None))
                &  (db.shops.uses > 9 )
                ).select( orderby=~db.shops.uses|db.shops.name ):
        #if not db.shops.uses or db.shops.uses < 1: continue
        img = None
        if r.icon: img = IMG(_src=URL('default','download', args=['db', r.icon], ))
        l.append(TR(TD(A(img or r.name, _href=r.url, _target='_blank'), _width=124, _class='center'),
                    TD(r.uses, _class='center' or ''), TD(r.descr or ''), _class='oll3'))
        l.append([TD(' ')])
    return locals()

def prices():
    response.title=False
    mess = CAT(
        H4(T('1. У нас нет абонентской платы.')),
        H4(T('2. Стоимость обслуживания берется:')),
        UL(
            T('с пользователей ввиде небольшогго процента от курса обмена криптовалют на биржах;'),
            T('с выплат Вам - с каждой выплаты около 2-3 комисиий сети.'),
            ),
        T('Комиссии сети можно посмотреть в списке '),
        A(T('описаний криптовалют'), _href=URL('default','currs')),
        )
    return locals()
