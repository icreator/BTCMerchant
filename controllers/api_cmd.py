# coding: utf8

# сессию не писать - и не тормозить другие апросы АЯКС
session.forget(response)

# разрешить использовать виды generic.*
# в локальном режиме все - в том числе и .html - который дает доступ к статистике
# не в локальном только .json и .xml
##response.generic_patterns = ['*'] if request.is_local else ['*.json','*.xml']
# там в генерик-файле стоит проверка на локальный вызов - так что можно разрешить
response.generic_patterns = ['*']

# возврашает результат работы команды
# по номеру магазина и уникальному хэшу команды для этогог магазина
def cmd_res():
    shop_id =  request.args(0)
    hash1 = request.vars.pop('cmd')
    if not shop_id or not hash1:
        raise HTTP(505, '/api/cmd_res/[shop_id]?cmd=HASH&PARS')

    key_r = db((db.shops_cmds.shop_id == shop_id) & (db.shops_cmds.hash1 == hash1))
    #print key_r
    cmd = key_r.select().first()
    if not cmd: return '{ "error": "command not found"}'

    # результат не удаляем !! del key_r
    # удаляем уведомление
    db(db.shop_orders_notes.cmd_id == cmd.id).delete()
    return cmd.res

# тут во входных параметрах обязательно должен быть хэш команды и ИД магазина
# http://127.0.0.1:8000/shop2/api/cmd/test/13?hash=sddfg345
def cmd():
    import shops_lib, urllib
    cmd_name = request.args(0)
    shop_id =  request.args(1)
    hash1 = request.vars.pop('hash')
    #hash1 = request.vars.get('hash')
    if not cmd_name or not shop_id or not hash1:
        raise HTTP(505, '/api/cmd/CMD_NAME/SHOP_ID?hash=HASH&PARS')
    shop = db.shops(shop_id)
    if not shop:
        raise HTTP(505, 'shop id not found')

    # тут мы еще комнду у себя не запоминали в базе
    # поэтому и счет и комнада = НОНЕ, а хэш в параметрах зададим для создания ссылки
    url = shops_lib.try_make_note_url(db, shop, None, None, {'cmd':hash1})
    log('cmd', url)
    f = urllib.urlopen(url)
    status = f.getcode()
    r = f.read()
    if status == 444 or r == hash1:
        cod = 444
        if cmd_name == 'test_cmd_resp':
            # это не команда а просьба выдать тестовый ответ
            # как будто команда уже исполнилась и выдала результат
            res = '{ "result": "success", "mess": "tested OK", "hash": %s }' % hash1
        else:
            if cmd_name == 'test_send_cmd':
                res = 'command tested, use now "test_cmd_resp" command for hash: %s' % hash1
            else:
                res = 'command inserted, hash: %s - wait for response' % hash1
                #request.vars['_cmd_name_'] = cmd_name
                id = db.shops_cmds.insert( shop_id = shop.id,
                                  name = cmd_name, hash1 = hash1, pars = request.vars)
                db.shops_cmds_stack.insert( ref_ = id, shop_id = shop.id, hash1 = hash1)
    else:
        res = 'command refused'
        cod = 200

    raise HTTP(cod, res)
