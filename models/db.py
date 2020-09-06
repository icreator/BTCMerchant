# coding: utf8

from decimal import Decimal

if not request.env.web2py_runtime_gae:
    ## if NOT running on Google App Engine use SQLite or other DB
    if DEVELOP:
        db = DAL(myconf.take('db.uri_dvp'), migrate = 1, check_reserved = ['all'])
    else:
        db = DAL(myconf.take('db.uri'), pool_size=myconf.take('db.pool_size', cast=int), check_reserved=['all'],
                fake_migrate = myconf.take('db.fake_migrate') or migrate,
                migrate = myconf.take('db.migrate') or migrate
                )
    ## в кукиях у пользователей хранить сессии - а не у нас на диске
    session.connect(request,response,cookie_key='kjykGFDRETfxf65',compression_level=None)
else:
    ## connect to Google BigTable (optional 'google:datastore://namespace')
    db = DAL('google:datastore+ndb')
    ## store sessions and tickets there
    session.connect(request, response, db=db)
    ## or store session in Memcache, Redis, etc.
    ## from gluon.contrib.memdb import MEMDB
    ## from google.appengine.api.memcache import Client
    ## session.connect(request, response, db = MEMDB(Client()))

# мой комп для разработки
db_ltc = DAL("sqlite://storage_ltc.sqlite", # on PC locals
    #pool_size=0,
    #migrate=True,
    check_reserved=['all'],
    )
# define new table
db_ltc.define_table('modules',
    Field('is_enabled', 'boolean', required=False, default=True),
    #Field('script', 'string', requires = IS_EMAIL(error_message=T('invalid email!')), length=128, required=True),
    Field('script', 'string', length=44, required=True),
    Field('ver', 'string', length=44, required=True),
    Field('url_shop', 'text'),
    Field('url_module', 'text'),
    Field('txt', 'text'),
    format = '%(script)s %(ver)s',
    #migrate='modules.table',
    #fake_migrate=True,
    )


db.define_table('currs',
    Field('abbrev', length=3, unique=True),
    Field('used', 'boolean', default=False, readable=False, comment='used by site'),
    Field('name', length=25, unique=True),
    Field('name2', length=25, unique=True, readable=False,
        comment='lower case for made a links (bitcoin, copperlark)'),
    Field('icon', 'upload'),
    Field('accuracy', 'integer', default = 2), # accuracy
    Field('add_change', 'integer', default = 5, comment='% for up price for fast accept'),
    Field('balance', 'decimal(17,8)', readable=False, default = Decimal(0)),
    Field('deposit', 'decimal(16,8)', readable=False, default = Decimal(0)), # то что нельзя выводить или продавать - запас для меня
    Field('shops_deposit', 'decimal(16,8)', readable=False, default = Decimal(0)), # то что нельзя выводить или продавать - запас магазинов
    Field('withdraw_over', 'decimal(16,8)', readable=False, default = Decimal('1.0')), # если больше то выплатим всем магазинам
    Field('fee_in', 'decimal(10,8)', readable=False, default = Decimal('0.000'), comment='=0 иначе мелкие входы не могут войти!!!'),
    Field('fee_out', 'decimal(10,8)', readable=False, default = Decimal('0.001'), comment='out'),
    Field('tax_in', 'decimal(4,2)', readable=False, default = Decimal('0.3'), comment='% tax for inputs'),
    Field('tax_out', 'decimal(4,2)', readable=False, default = Decimal('0.0'), comment='% tax for outputs'),
    Field('url', length=50, unique=False),
    Field('desr', 'text'),
    migrate=True,
    #fake_migrate=True,
    redefine=True, # пересоздать table
    format='%(abbrev)s',
    )
def get_curr_name(r):
    return db.currs[r.curr_id].abbrev
# CRYPTO
db.define_table('xcurrs',
    Field('id', readable=False),
    Field('curr_id', db.currs, readable=False),
    Field('first_char', length=2, readable=False, comment='insert in db.common.get_currs_by_addr !!!'), # для быстрого поиска крипты по адресу
    Field('connect_url', length=99, readable=False, default='http://user:pass@localhost:3333', unique=True),
    Field('block_time', 'integer', comment='in sec. BTC = 600sec'),
    Field('txfee', 'decimal(10,8)', default = Decimal('0.0001'), comment='For one pay_out transaction. Payed to web'),
    Field('conf_soft', 'integer', default = 0, comment='confirmations for accept as SOFT status'),
    Field('conf_hard', 'integer', default = 1),
    Field('conf_true', 'integer', default = 3),
    Field('conf_gen', 'integer', default = 120, readable=False, comment='confirmations for accept generated coins'),
    Field('from_block', 'integer', readable=False, comment='block was tested'),
    #migrate=False,
    #redefine=True, # пересоздать table
    format=get_curr_name,
    )

# eFIAT
db.define_table('ecurrs',
    Field('curr_id', db.currs),
    #redefine=True, # пересоздать table
    format=get_curr_name,
    )

#
db.define_table('exchgs',
    Field('name', length=25, unique=True),
    Field('used', 'boolean', default=False, comment='used by site'),
    Field('url', length=55, unique=True),
    Field('tax', 'decimal(4,3)', required=True, default=0.2, comment='tax % for one order'),
    Field('fee', 'decimal(5,3)', required=True, default=0, comment='absolut fee for one order'),
    Field('API_type', length=15, comment='API type = upbit, btce'),
    Field('API', 'text', comment='API commands and urls in JSON format'),
    Field('pkey', 'text', comment='public key'),
    Field('skey', 'text', comment='secret key'),
    #redefine=True, # пересоздать table
    format='%(name)s',
    )

# the need set ticker name on this ecchange an limits of reserves and sells
db.define_table('exchg_limits',
    Field('exchg_id', db.exchgs),
    Field('curr_id', db.currs),
    # btc, rur ...
    Field('ticker', length=7, required=True, comment='set TICKET name for this exchange (default = lower(xcurr). ...btc, rur'),
    Field('reserve', 'decimal(16,6)', comment='reserve balance, not sale'),
    Field('sell', 'decimal(16,6)', comment='limit for one sale'),
    Field('buy', 'decimal(16,6)', comment='limit for one buy'),
    #redefine=True, # пересоздать table
    format='%(curr_id)s %(ticker)s',
    )
# тут сделаем уникальный сложную проверку
db.exchg_limits.exchg_id.requires=IS_IN_DB(db, 'exchgs.id', '%(name)s',
    _and = IS_NOT_IN_DB(db(db.exchg_limits.curr_id==request.vars.curr_id),'exchg_limits.exchg_id'))

db.exchg_limits.curr_id.requires=IS_IN_DB(db, 'currs.id', db.currs._format,
    _and = IS_NOT_IN_DB(db(db.exchg_limits.exchg_id==request.vars.exchg_id),'exchg_limits.curr_id'))

# мои таксы обменов
db.define_table('exchg_taxs',
    Field('curr1_id', db.currs),
    Field('curr2_id', db.currs),
    Field('tax', 'decimal(5,2)', comment='tax %'),
    )
# тут сделаем уникальный сложную проверку
db.exchg_taxs.curr1_id.requires=IS_IN_DB(db, 'currs.id', '%(name)s',
    _and = IS_NOT_IN_DB(db(db.exchg_taxs.curr2_id==request.vars.curr2_id),'exchg_taxs.curr1_id'))
db.exchg_taxs.curr2_id.requires=IS_IN_DB(db, 'currs.id', '%(name)s',
    _and = IS_NOT_IN_DB(db(db.exchg_taxs.curr1_id==request.vars.curr1_id),'exchg_taxs.curr2_id'))

db.define_table('exchg_pairs',
    Field('exchg_id', db.exchgs),
    Field('used', 'boolean', default=False, comment='used by site'),
    Field('curr1_id', db.currs),
    Field('curr2_id', db.currs),
    Field('ticker', length=12, comment='pair id - 132 on cryptsy DOGE-BTC'),
    Field('on_update', 'datetime', writable=False,
         default=request.now,
         update=request.now, # contains the default value for this field when the record is updated
         ),
# depth
    Field('sp1', 'decimal(16,8)'), # price up 1% from curr sell price
    Field('sv1', 'decimal(16,8)'), # selled volume up 1% from curr sell price
    Field('bp1', 'decimal(16,8)'), # buyed volume up 1% from curr buy price
    Field('bv1', 'decimal(16,8)'),
    #redefine=True, # пересоздать table
    #migrate=False,
    format='%(exchg_id)s %(curr1_id)s %(curr2_id)s',
   )
db.exchg_pairs.exchg_id.requires=IS_IN_DB(db, 'exchgs.id', '%(name)s',
    _and = IS_NOT_IN_DB(db((db.exchg_pairs.curr1_id==request.vars.curr1_id) & (db.exchg_pairs.curr2_id==request.vars.curr2_id)),'exchg_pairs.exchg_id'))
db.exchg_pairs.curr1_id.requires=IS_IN_DB(db, 'currs.id', db.currs._format,
    _and = IS_NOT_IN_DB(db((db.exchg_pairs.exchg_id==request.vars.exchg_id) & (db.exchg_pairs.curr2_id==request.vars.curr2_id)),'exchg_pairs.curr1_id'),
       )
db.exchg_pairs.curr2_id.requires=IS_IN_DB(db, 'currs.id', db.currs._format,
    _and = IS_NOT_IN_DB(db((db.exchg_pairs.exchg_id==request.vars.exchg_id) & (db.exchg_pairs.curr1_id==request.vars.curr1_id)),'exchg_pairs.curr2_id'))

db.define_table('exchg_pair_bases',
    Field('curr1_id', db.currs),
    Field('curr2_id', db.currs),
    Field('hard_price', 'decimal(16,8)'), # hard price - if >0 - not  use sp-sv values
    Field('base_vol', 'decimal(16,8)'),
    Field('base_perc', 'decimal(5,3)', comment='%'),
    )
###############################################################
# наши работники - дилеры, подключающие к нам магазины
db.define_table('dealers',
    Field('FIO', length=50, unique=False, label=T('ФИО')),
    Field('doc', length=50, unique=True, label=T('Документ')),
    Field('email', length=60, unique=False, required=False,
        requires = IS_EMAIL(error_message=T('invalid email!'))
        ), # для отправки уведомлений плательщику
    format='%(doc)s %(FIO)s',
    )
db.define_table('dealers_xwallets',
    Field('dealer_id', db.dealers),
    Field('xcurr_id', db.xcurrs),
    Field('addr', length=100, required=True),
    Field('bal', 'decimal(16,8)', default=Decimal(0.0)),
    #redefine=True, # пересоздать table
    format='%(dealer_id)s %(xcurr_id)s %(addr)s',
    )



######################################################################
db.define_table('shops_cat',
    Field('name', length=50,  unique=True),
    #redefine=True, # пересоздать table
    format='%(name)s',
    )

# тут все настройки платежей для данного дела - мин и макс платеж, вылюта выхода и пр
# валюты входа отдельно, сначала пользователи на дело, потомвалта входа на пользователя
def format_shops(r):
    return r.url or r.name or r.email

db.define_table('shops',
    Field('cat_id', db.shops_cat, default = 1),
    Field('simple_curr', 'integer', comment='=curr id if name == wallet adress'),
    Field('name', length=50, unique=False), # for URL and LABELs
    Field('url', length=125, comment='http://demo_shop.com - url to shop'), #
    Field('email', length=60,
        requires = IS_EMPTY_OR(
            IS_EMAIL(error_message=T('Неправильный емайл!')),
            )),
    Field('icon', 'upload'),
    Field('icon_url', length=60, comment='"static/images/logo.png"'), # вместо загрузки файла
    Field('show_text', 'text'),
    Field('not_used', 'boolean'),
    Field('note_url', 'text', comment='"index.php?route=payment/cryptopay/callback&"'), # после оплаты куда идти
    Field('note_on', length=15),
    Field('back_url', 'text', comment='"index.php?route=account/order/info&order_id="'), # эта ссылка должна складываться со ссылкой на магазин
    Field('dealer_id', db.dealers, #required=False,
          requires = IS_EMPTY_OR(IS_IN_DB(db, 'dealers.id', '%(doc)s %(FIO)s'))
          ),
    #Field('dealer_id', 'reference db.dealers', required=False), #requires='reference dealers'),
    Field('tax', 'decimal(4,2)', default = 0.3, comment='%  мне за это дело'),
    Field('not_listed', 'boolean'),
    Field('descr', 'text'),
    Field('average', 'decimal(16,8)', default = 0, comment='average income'),
    Field('uses', 'integer', default = 0), # used
    Field('created_on', 'datetime', writable=False, default=request.now),
    #redefine=True, # пересоздать table
    format=format_shops,
    )
# магазин на добавление - пока не будет подмтвержден адрес выплат он тту как тЕСТОВЫЙ
db.define_table('shops_add',
    Field('cat_id', db.shops_cat, default = 1),
    Field('name', length=50,  unique=False, required=True), # for URL and LABELs
    Field('url', length=60, unique=False, required=True, comment='url to shop'), #
    Field('email', length=60, required=False, readable=False,
        requires = IS_EMAIL(error_message='invalid email!')),
    Field('icon', 'upload', readable=False),
    Field('CMS', length=50, comment=T('с помошью какого CMS Framework был написан Ваш магаин?')),
    Field('show_text', 'text', readable=False,),
    Field('note_url', 'text', readable=False, unique=False, required=True, comment='url for notify'), # после оплаты куда идти
    Field('note_on', length=15, readable=False, comment='HARD'),
    Field('back_url', 'text', readable=False, comment=T('Ссылка для возврата назад в магазин (общие правила как и для ссылки note_url')), # эта ссылка должна складываться со ссылкой на магазин
    Field('descr', 'text', readable=False, comment=T('Описание магазина')),
    Field('wallet_BTC', readable=False, length=50, unique=True, required=True, comment='Your BTC waller address'),
    Field('wallet_LTC', readable=False, length=50, unique=True, required=False, comment='Your LTC waller address'),
    format='%(name)s',
    )

db.define_table('shops_balances',
    Field('shop_id', db.shops),
    Field('curr_id', db.currs),
    Field('kept', 'decimal(16,8)', default=Decimal(0.0)), # то что удержано на сервисе для расчетов по командам
    Field('bal', 'decimal(16,8)', default=Decimal(0.0)),
    Field('withdraw_over', 'decimal(16,8)', default=Decimal(1.0)), # если баланс больше то выплатим
    Field('updated_on', 'datetime', writable=False, default=request.now, update=request.now ),
    #redefine=True, # пересоздать table
    format='%(shop_id)s %(curr_id)s %(bal)s',
    )
# стек для команд от магазинов
db.define_table('shops_cmds',
    Field('shop_id', db.shops),
    Field('name', length=15),
    Field('hash1', 'integer'),
    Field('pars', 'json'),
    Field('created_on', 'datetime', default=request.now ),
    Field('res', 'json'),
    Field('res_on', 'datetime' ),
    )
db.define_table('shops_cmds_stack', # чтобы не проверять те что уже исполнились и оповестились
    Field('ref_', db.shops_cmds),
    Field('shop_id', db.shops), # уникальность для отдельного магазина будет
    Field('hash1', 'integer'),
    Field('status', length=3),
    )

db.define_table('shops_xwallets',
    Field('shop_id', db.shops),
    Field('xcurr_id', db.xcurrs),
    Field('addr', length=50, required=True),
    Field('bal', 'decimal(16,8)', default=Decimal(0.0)),
    Field('payouted', 'decimal(16,8)', default=Decimal(0.0)),
    #redefine=True, # пересоздать table
    format='%(shop_id)s %(xcurr_id)s %(addr)s',
    )
# для конвертации через 7pay.in
# запомним тут адреса фиатных кошельков для магазинов
# держатели валюты - qiwi, YD, mail.ru, PayPal,...
db.define_table('fiat_dealers',
    Field('name', length=20, unique=True),
    Field('abbrev', length=3, unique=True),
    #redefine=True, # пересоздать table
    format='%(name)s',
    )

db.define_table('shops_ewallets',
    Field('shop_id', db.shops),
    Field('dealer_id', db.fiat_dealers),
    Field('ecurr_id', db.ecurrs),
    Field('pay_out_MIN', 'decimal(6,2)', default=Decimal(10.0), comment='MIN paymennt for this ecurr and edialer'),
    Field('addr', length=40, required=True),
    Field('bal', 'decimal(16,3)', default=Decimal(0.0)),
    #redefine=True, # пересоздать table
    format='%(shop_id)s %(dealer_id)s %(ecurr_id)s %(addr)s',
    )
########################################################################
# тут только персональные данные пользователя для данного дела
# - его ИД или телефон и т.д - то что надо указать в платежке для диллера
def format_shop_orders(r):
    shop = db.shops[r.shop_id]
    abbr = db.currs[r.curr_id].abbrev
    return '%s:%s [%s] %s' % (r.id, r.order_id, format_shops(shop), abbr)
#######################################################################
db.define_table('shop_orders',
    Field('shop_id', db.shops),
    Field('curr_id', db.currs),
    Field('order_id', length=50, required=False), # тут все коды через пробел
    Field('price', 'decimal(18,8)'), # если задано то это стоимость заказа - ее нужно всю собрать
    Field('conv_curr_id', db.currs, # валюта в которую конвертировать
                requires = IS_EMPTY_OR(IS_IN_DB(db, 'currs.id', '%(abbrev)s'))),
    Field('vol_default', 'decimal(18,8)'), # если указано то задавать значание по умолчанию в поле счета
    Field('keep', 'decimal(6,5)', default=Decimal(0)), # то что остается (удержано) на сервисе и не пересылается в магазин 1=все остается
    Field('expire', 'integer', comment='in minits, =0 not expired', default=0), # минут до протухания
    Field('mess', 'text'),
    # по умолчанию делаем все секртным, парам &public при создании отменяет это - тут Пусто будет
    Field('secr', length=10), # если задано то АПИ выдается только по секрету
    Field('lang', length=10),
    Field('curr_in', 'json'),
    Field('curr_in_stop', 'json'),
    Field('not_convert', 'boolean'), # не конвертировать в валюту выхода - править балансы для входящих валют
    Field('exchanging', 'boolean'), # - это для обменных операций, не больше чем резервы сервиса
    Field('addrs', 'json', comment='{"addr1":3, "addr2":5, ...}'), # если задан то вывод на них пропроционально весу а не в магаз
    Field('addrs_outs', 'json', comment='{"addr1":12.34, "addr2":456.1234, ...}'), # сколько и кому было выплочено - если задан тут addrs
    Field('status', length=15, default='NEW'),
    Field('payed_soft', 'decimal(18,8)', default=Decimal(0.0)), # сколько уже поступило мягких платжей
    Field('payed_hard', 'decimal(18,8)', default=Decimal(0.0)), # сколько уже поступило твердых платжей
    Field('payed_true', 'decimal(18,8)', default=Decimal(0.0)), # сколько уже поступило правдивых платжей
    Field('email', length=60, unique=False, required=False,
        requires = IS_EMPTY_OR(IS_EMAIL(error_message=T('invalid email!')))
        ), # для отправки уведомлений плательщику
    Field('created_on', 'datetime', writable=False, default=request.now),
    Field('note_on', length=15),
    Field('back_url', length=125), # эта ссылка должна складываться со ссылкой на магазин
    #redefine=True, # пересоздать table
    format=format_shop_orders,
    )
# для закрытия заказов
db.define_table('shop_orders_stack',
    Field('ref_id', db.shop_orders),
    Field('expire_on', 'datetime'),
    format='%(ref_id)s',
    )
db.define_table('shop_orders_notes',
    Field('ref_id', 'reference shop_orders'),
    Field('cmd_id', 'reference shops_cmds'),
    Field('created_on', 'datetime', writable=False, default=request.now),
    Field('tries', 'integer', default=0), # попыток былоо сообщить - чтобы время задержки увеличивать
    #redefine=True, # пересоздать table
    )

# для входов разных приптовалют
# - адреса в разных кошельках
def format_shop_order_addrs(r):
    shop_order = db.shop_orders[r.shop_order_id]
    xcurr = db.xcurrs[r.xcurr_id]
    return '%s <-[%s] %s' % (format_shop_orders(shop_order), get_curr_name(xcurr), r.addr)

# криптоадреса для одного счета по разным криптам
db.define_table('shop_order_addrs',
    Field('shop_order_id', db.shop_orders),
    Field('unused', 'boolean', default=False, comment='if stolen or unused by site'),
    Field('xcurr_id', db.xcurrs), # тут валюта ВЫходящая
    Field('addr', length=50, required=True), # его адрес в кошельке крипты
#    Field('amount', 'decimal(16,8)', default=Decimal(0.0)), # сколько крипты пришло
#    Field('in_block', 'integer'), # какой блок последнего входа - по нему статус оплаты этой криптой
#    Field('amo_out', 'decimal(16,8)', default=Decimal(0.0)), # сколько крипты зачли по курсу
    #redefine=True, # пересоздать table
    format=format_shop_order_addrs,
    )

##################################################################################
# в ЗАКАЗАХ стопорится курс обмена для данной крипты данного дела пользователя
#
db.define_table('rate_orders',
    Field('ref_id', db.shop_order_addrs),
    Field('created_on', 'datetime', writable=False, default=request.now),
    Field('volume_in', 'decimal(18,10)'),
    Field('volume_out', 'decimal(18,10)'),
    Field('used_amo', 'decimal(18,10)', default=Decimal(0.0)), # какое кол-во мы уже по нему учли входов
    Field('status', length=3),
    #redefine=True, # пересоздать table
    )
# вновь созданные ордера создают тут записи тоже
# оплата по ордерам идет сюда, если время ордера вышло или он оплачен
# запись из стека удаляется так чтобы не мешаться
# а основная таблица ордеров - это как архив
db.define_table('rate_orders_stack',
    Field('ref_id', db.rate_orders),
    Field('created_on', 'datetime', writable=False, default=request.now),
    #redefine=True, # пересоздать table
    )

####################################################################
####################################################################

# если у счета автовыплаты стоя то зозданим записи на выплаты по счету а не по магазину
# в этом случае у магазина делаем 0-ю транзакцию и не меняем баланс
db.define_table('bills_draws',
    Field('shop_order_id', db.shop_orders),
    Field('curr_id', db.currs),
    Field('addr', length=50), #
    Field('amo', 'decimal(16,8)', default=Decimal(0.0)), # если это не обмен то вход или выход может быть с 0
    #Field('desc_', 'text'), # сюда пишем
    Field('created_on', 'datetime', writable=False, default=request.now),
    )
# транзакции выплат по автовыплатам в счетах
db.define_table('bills_draws_trans',
    Field('shop_order_id', db.shop_orders),
    Field('curr_id', db.currs),
    Field('txid', length=70), # транзакция
    Field('amo', 'decimal(16,8)'),
    )
#############################################################################
# тут если вход или выход = 0 или валюта неизвестна или = входу, значит
# это не обмен внутри в вход извне или вывод вовне на счета клиента
# сюда же поидее пишем выплаты у счетов у которых заданы адреса для авто-выплат - только с минусом
db.define_table('shops_trans',
    Field('shop_order_id', db.shop_orders),
    Field('curr_id', db.currs),
    Field('amo', 'decimal(16,8)', default=Decimal(0.0)), # если это не обмен то вход или выход может быть с 0
    Field('desc_', 'text'), # сюда пишем
    Field('created_on', 'datetime', writable=False, default=request.now),
    #redefine=True, # пересоздать table
    #migrate=False,
    )
# то что выплатили магазинам
db.define_table('shops_draws',
    Field('shop_id', db.shops),
    Field('curr_id', db.currs),
    Field('amo', 'decimal(16,8)', default=Decimal(0.0)), # если это не обмен то вход или выход может быть с 0
    Field('desc_', 'text'), # сюда пишем
    Field('created_on', 'datetime', writable=False, default=request.now),
    #redefine=True, # пересоздать table
    #migrate=False,
    )

# подписка для клиентов
db.define_table('news_descrs',
    Field('email', length=60, unique=True,
        requires = [IS_EMAIL(error_message=T('Неправильный емайл!')),
                    IS_NOT_IN_DB(db, 'news_descrs.email')]),
    #redefine=True, # пересоздать table
    format='%(email)s',
    )

####################################################################
####################################################################
####################################################################
####################################################################

# какие суммы пришли на какой адресс
# по этим данным найдем дело в deals_income
def format_pay_ins(r):
    return '%s:%s %s %s' % ( r.id,
        format_shop_order_addrs(db.shop_order_addrs[r.shop_order_addr_id]),
        r.rate_order_id and 'rate_order_id: %s' % r.rate_order_id or 'free_rate',
        ##r.shop_id and format_shops(db.shops[r.shop_id]) or 'not_Shop',
        r.amount
        )

    pass
db.define_table('pay_ins',
    Field('shop_order_addr_id', db.shop_order_addrs), #  кому мы ее причислили
    Field('rate_order_id', 'integer'), # db.rate_orders), # какой курс был использован
    ###Field('shop_id', 'integer'), # db.shops), # кому одадим этот вход
    Field('amount', 'decimal(16,8)', comment='value received'),
    Field('amo_out', 'decimal(16,8)', comment='value converted'), # как только подтверждение случилось - запоминаем сконвертированное значение
    Field('created_on', 'datetime', writable=False), # сами должны вставить default=request.now),
    Field('status', length=15, default='NEW'), # новые плтежи все как NEW
    Field('status_dt', 'datetime', writable=False), # время смены статуса
    Field('amo_ret', 'decimal(16,8)', comment='value returned'),
    Field('in_block', 'integer'),
    Field('txid', length=70), # транзакция
    Field('vout', 'integer'), # выход в транзакции
    # что с платежом - зачислен, конвертирован, оплачен диллеру/поставщику
    #redefine=True, # пересоздать table
    #migrate=False,
    format=format_pay_ins,
    )
# стек платежей которые на проплату -
db.define_table('pay_ins_stack',
    Field('ref_id', db.pay_ins),
    Field('xcurr_id', db.xcurrs),
    Field('in_block', 'integer'),
    #redefine=True, # пересоздать table
    )
# сколько и кому надо вернуть
db.define_table('pay_ins_return',
    Field('ref_id', db.pay_ins),
    Field('xcurr_id', db.xcurrs),
    Field('in_block', 'integer'),
    Field('txid', length=70), # транзакция
    Field('vout', 'integer'), # выход в транзакции
    Field('amount', 'decimal(16,8)'),
    Field('addr', length=50),
    )
# сколько и кому надо вернуть
db.define_table('pay_ins_returned',
    Field('ref_id', db.pay_ins),
    Field('txid', length=70), # транзакция
    Field('vout', 'integer'), # выход в транзакции
    Field('amount', 'decimal(16,8)'),
    Field('addr', length=50),
    )

#######################################################
#################################
# создаем споры
db.define_table('wagers', # идентификатор спора - паридля платежного сервиса
    Field('shop_id', db.shops),
    Field('curr_id', db.currs),
    Field('secr_key','string', length=10),
    Field('status','string', length=10, requires=IS_IN_SET(['PAY', 'RUN', 'END']), default = 'PAY'),
    Field('total', 'decimal(16,8)', default = Decimal('0.0')),
    Field('keep', 'decimal(5,4)', default = Decimal('0.98'), comment='as many keep for pay_outs'),
    Field('run_dt', 'datetime', comment='auto run DT'),
    Field('maker_fee', 'decimal(5,4)', default = Decimal('0.03'), comment='fee for maker'),
    Field('maker_addr', 'string', length=60, comment=' maker wallet address'),
    Field('bill_ids','list:integer', default = [], comment='list of bills ID for this wager'),
    Field('winner_ids','list:integer', comment='list of bills ID that win'),
    format = '%(id)s',
    )
db.define_table('wagers_stack', # идентификатор спора - паридля платежного сервиса
    Field('ref_id', db.wagers),
    Field('curr_id', db.currs),
    Field('created_on', 'datetime', writable=False, default=request.now),
    Field('status','string', length=10, requires=IS_IN_SET(['PAY', 'RUN', 'END']), default = 'PAY'),
    )

#####################################################################
# если наша созданная транзакция не включена в блок,
# то запустить ее в сеть поновой надо?
db.define_table('xcurrs_raw_trans',
    Field('xcurr_id', db.xcurrs),
    Field('txid', length=70), # дело в котром крипта использовалась
    Field('tx_hex', 'text'),
    Field('confs', 'integer'),
    #redefine=True, # пересоздать table
    )

#######################################################
###       STATISTICS
#####################################################################
db.define_table('currs_stats',
    Field('curr_id', db.currs), # тут валюта входящая
    Field('shop_id', db.shops), # дело в котром крипта использовалась
    Field('average', 'decimal(16,8)', default = 0, comment='average income'),
    Field('count_', 'integer'),
    #redefine=True, # пересоздать table
    )

db.define_table('news',
    Field('on_create', 'datetime', writable=False, default=request.now, update=request.now,  ),
    Field('head', length=100),
    Field('body', 'text'),
    #redefine=True, # пересоздать table
    format='%(head)s',
    )

db.define_table('recl',
    Field('on_create', 'datetime', writable=False, default=request.now, update=request.now,  ),
    Field('url', length=200),
    Field('count_', 'integer', default = 0),    # сколько раз показали
    Field('level_', 'integer', default = 0),    # уровень стоимости рекламы - гдде ее показывать
    #redefine=True, # пересоздать table
    format='%(url)s',
    )

#######################
def make_found_url(r):
    shop = db(db.shops.name=='startup').select().first()
    if not shop: return ''
    return A(T('Внести'), _href=URL('order', 'show', args=[shop.id],
               vars={'order': r.startup.passport, 'curr': 'CLR', 'vol': 0.1,
                     #'curr_in': 'BTC'
                     })
               )
db.define_table('startup',
    Field.Virtual('found_url', lambda r: make_found_url(r), label=T('Взнос')),
    #Field.Virtual('found_url', lambda r: r.FIO, label=T('Оплатить')),
    #Field.Virtual('deal_url', lambda r: A(T('Перейти'), _href=URL('more','to_pay', args=[r.startup.id])), label=T('Ссылка')),
    Field('email', length=60, unique=True, readable=False,
        requires = [IS_EMAIL(error_message=T('Неправильный емайл!')),
                    IS_NOT_IN_DB(db, 'startup.email')]),
    Field('FIO', label=T('ФИО полностью'), length=100),
    Field('passport', 'decimal(11,0)', label=T('Паспорт'), comment=T('Только цифры 4500123456'), unique=True, readable=False,
        requires = [IS_DECIMAL_IN_RANGE(99999,9999999999),
                    IS_NOT_IN_DB(db, 'startup.passport')]),
    #Field('icon', 'upload', readable=False, label=T('Файл'), comment=T('Копия паспорта')),
    Field('founded', 'decimal(16,3)', default=Decimal(0), writable=False, label=T('Оплачено, CLR')),
    Field.Virtual('founded_uk', lambda r: round(float(r.startup.founded * 10000),2), label=T('Намерение, руб')),
    #Field('addr', length=50, writable=False, comment=T('Биткоин адрес для взносов')),
    Field('on_create', 'datetime', label=T('Участие с'), writable=False, default=request.now, update=request.now,  ),
    Field('mess', 'text', label=T('Сообщение'), readable=False),
    #redefine=True, # пересоздать table
    format='%(mess)s',
    )

db.define_table('vacs', # вакансии
    Field('on_create', 'datetime', writable=False, default=request.now, update=request.now,  ),
    Field('job', label=T('Должность')),
    Field('expertise', 'text', label=T('Что умеете')),
    Field('contacts', 'text', label=T('Как связаться'), readable=False,),
    #redefine=True, # пересоздать table
    format='%(job)s',
    )

db.define_table('logs',
    Field('on_create', 'datetime', writable=False, default=request.now, update=request.now,  ),
    Field('label123456789', length=20, label='label123456789'),
    Field('label1234567890', length=20, label='label987654321'),
    Field('mess', 'text'),
    #redefine=True, # пересоздать table
    format='%(mess)s',
    )


# define new table
db.define_table('modules',
    Field('is_enabled', 'boolean', required=False, default=True),
    #Field('script', 'string', requires = IS_EMAIL(error_message=T('invalid email!')), length=128, required=True),
    #Field('script', 'string', length=44, required=True),
    Field('ver', 'string', length=44, required=True),
    Field('url_shop', 'text'),
    Field('url_module', 'text'),
    Field('txt', 'text'),
    format = '%(script)s %(ver)s',
    #migrate='modules.table',
    #fake_migrate=True,
    )

def pop_all(db):
    #############################################################
    ################################################################
    for t in ['exchg_taxs', 'exchg_limits', 'exchg_pairs', 'exchgs',
             'ecurrs', 'xcurrs', 'currs']:
        if db(db[t]).isempty(): db[t].truncate()
    ############################################################
    if db_ltc(db_ltc.modules).isempty():
        db_ltc.modules.truncate()
        for r in [
                ['PrestaShop', '1.5+', 'https://www.prestashop.com',
                 'https://www.prestashop.com/forums/topic/347034-bitcoin-merchant-free-module/?p=1748226', 'World'],
                ['OpenCart', '2.0.1.1', 'http://www.opencart.com/',
                 'https://opencartforum.com/files/file/2037-%D0%BF%D0%BB%D0%B0%D1%82%D0%B5%D0%B6%D0%B8-%D0%B2-%D0%B1%D0%B8%D1%82%D0%BA%D0%BE%D0%B8%D0%BD-%D0%BD%D0%B0-%D1%81%D0%B0%D0%B9%D1%82/', 'Russian'],
                ['OpenCart', '2.0.1.1', 'http://www.opencart.com/',
                 'http://www.opencart.com/index.php?route=extension/extension/info&extension_id=20646', 'World'],
                ['OpenCart', '1.5.6.4', 'http://www.opencart.com/',
                 'http://www.opencart.com/index.php?route=extension/extension/info&extension_id=20646', 'World'],
                ]:
            db_ltc.modules.insert( is_enabled = True, script = r[0], ver = r[1],
                            url_shop = r[2], url_module=r[3], txt=r[4])
        
    if db(db.currs).isempty():
        for r in [
                ['BTC', True, 'Bitcoin', 'bitcoin', 8, 'http://bitcoin.org', 'Main cryptocurrency'], # 1
                ['LTC', True, 'Litecoin', 'litecoin', 8, 'http://litecoin.org','lite'],
                ['DGE', True, 'Dogecoin', 'dogecoin', 8, 'http://dogecoin.com','lite'],
                ['NVC', True, 'Novacoin', 'novacoin', 8, 'http://novacoin.org','lite'],
                ['PPC', True, 'Peercoin', 'peercoin', 8, 'http://peercoin.net','lite'],
                ['DSC', True, 'Dashcoin', 'dashcoin', 8, 'http://dash.net','lite'],
                ['USD', True, 'Dollar US', 'dollar us', 2, None,' fiat money'], # 7
                ['EUR', True, 'Euro', 'euro', 2, None,' fiat money'],
                ['RUB', True, 'Рубль', 'Russian Ruble', 2, None,' fiat money'],
                ['AUD', True, 'Australian Dollar', None, 2, None,' fiat money'],
                ['TRY', True, 'Turkish Lira', None, 2, None,' fiat money'],
                ['NZD', True, 'New Zealand Dollar', None, 2, None,' fiat money'],
                ['PHP', True, 'Philippines Peso', None, 2, None,' fiat money'],
                ]:
            db.currs.insert( abbrev = r[0], used = r[1],
                            name = r[2], name2=r[3], accuracy=r[4], url=r[5], desr=r[6])

    if db(db.xcurrs).isempty():
        for r in [
                [1, '13', 'http://qq:qq@127.0.0.1:8332', 600, 0.00005, 0, 1, 3, 100, 392961], # BTC
                [2, 'L3', 'http://qq:qq@127.0.0.1:9332', 150, 0.001, 0, 2, 5, 100, 920579], # LTC
                [3, 'D9A', 'http://qq:qq@127.0.0.1::9432', 30, 1, 1, 5, 25, 100, 1040927], # DOGE
                [4, '4', 'http://qq:qq@127.0.0.1::10332', 450, 0.01, 0, 1, 4, 100, 228724], # NVC
                [5, '', 'http://qq:qq@127.0.0.1::11332', 300, 0.01, 0, 1, 3, 100, 228724], # PPC
                [6, '', 'http://qq:qq@127.0.0.1::12332', 300, 0.01, 0, 1, 3, 100, 228724], # DASH
                ]:
            db.xcurrs.insert(curr_id=r[0], first_char=r[1], connect_url=r[2],
                             block_time=r[3], txfee=r[4], conf_soft=r[5], conf_hard=r[6], conf_true=r[7], conf_gen=r[8], from_block=r[9])

    if db(db.ecurrs).isempty():
        for r in [
                [7], # USD
                [8], # EURO
                [9], # RUB
                [10], # 
                [11], # 
                [12], # 
                [13], # 
                ]:
            db.ecurrs.insert(curr_id=r[0])

    #################

    if db(db.exchgs).isempty():
        for r in [
                ['BTC-e', True, 'btc-e.com', 0.2, 0, 'btce'],
                ['cryptsy', True, 'www.cryptsy.com', 0.2, 0, 'cryptsy'],
                ['Yahoo', True, '', 1, 0, 'fiat'],
                ['PayPal', True, 'pp', 1, 0, 'fiat'],
                ]:
            db.exchgs.insert( name = r[0], used = r[1], url = r[2], tax=r[3], fee=r[4], API_type=r[5])

    if db(db.exchg_limits).isempty():
        for r in [
                [1, 9, 'rur'], # ticker for ruble - rur
                [2, 2, 'DOGE'], # ticker for dogecoin - DOGE
                ]:
            db.exchg_limits.insert( exchg_id = r[0], curr_id = r[1], ticker = r[2])

    if db(db.exchg_pairs).isempty():
        for r in [
                [1, True, 1, 7, ''], # btc-e.com BTC-USD
                [1, True, 1, 8, ''], # btc-e.com BTC-EUR
                [1, True, 1, 9, ''], # btc-e.com BTC-RUR
                [1, True, 2, 1, ''], # btc-e.com LTC-BTC
                [1, True, 2, 7, ''], # btc-e.com LTC-USD
                [1, True, 2, 8, ''], # btc-e.com LTC-RUB
                [1, True, 4, 1, ''], # btc-e.com NVC-BTC
                [1, True, 5, 1, ''], # btc-e.com PPC-BTC
                [2, True, 3, 1, '132'], # cryptsy.com DOGE-BTC - ticker for pair = 132
                #[3, True, 7, 6, ''], # Yahoo RUB-USD
                [3, True, 8, 6, ''], # Yahoo 
                [3, True, 9, 6, ''], # Yahoo 
                [3, True, 10, 6, ''], # Yahoo 
                [3, True, 11, 6, ''], # Yahoo 
                [3, True, 12, 6, ''], # Yahoo 
                [3, True, 13, 6, ''], # Yahoo 
                #[4, True, 12, 0],
                ]:
            db.exchg_pairs.insert( exchg_id = r[0], used = r[1], curr1_id = r[2], curr2_id=r[3], ticker=r[4])

pop_all(db)
