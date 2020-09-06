#!/usr/bin/env python
# coding: utf8
import datetime

def log(db, l2, mess='>'):
    m = 's_cmds'
    print m, mess
    db.logs.insert(label123456789=m, label1234567890=l2, mess='%s' % mess)
def log_commit(db, l2, mess='>'):
    log(db, l2, mess)
    db.commit()

def del_note(db, cmd):
    if not cmd: return
    #print 'del NOTE for shop_order.id:', shop_order.id
    try:
        db(db.shop_orders_notes.cmd_id == cmd.id).delete()
    except:
        pass

def make_note(db, cmd):
    shop_orders_note = db(db.shop_orders_notes.cmd_id == cmd.id).select().first()
    if shop_orders_note:
        log(db, 'make_note', 'update NOTE[%s] tryes = 0 ' % shop_orders_note.id)
        shop_orders_note.update_record( tries = 0 )
    else:
        id = db.shop_orders_notes.insert(cmd_id = cmd.id)
        log(db, 'make_note', 'insert NOTE[%s] for cmd.id = %s' % (id, cmd.id))


def proc(db, cmd_s):
    cmd = db.shops_cmds[ cmd_s.ref_ ]
    if not cmd:
        try:
            # если вдруг команды у стека нет
            del db.shops_cmds_stack[ cmd_s.id ]
        except:
            pass
        return
    nm = cmd.name
    res = None
    if nm == 'send_many':
        pass
    else:
        # если неизвестная команда то это тест - закатаем результат в нее и на уведомление
        cmd.update_record( res = '{ "result": "success", "mess": "tested OK", "hash": %s }' % cmd.hash1,
                  res_on = datetime.datetime.now() )
        make_note(db, cmd)

    # команда выполнена даже если с ошибкой - удалим ее из стека
    del db.shops_cmds_stack[ cmd_s.id ]

def run(db):
    for cmd_s in db(db.shops_cmds_stack).select():
        log(db,'run', cmd_s)
        proc(db, cmd_s)
