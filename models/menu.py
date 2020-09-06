# -*- coding: utf-8 -*-

response.menu = [
    (
        #T('About'),
        H3(XML('<i class="fa fa-home"></i>')),
        0, URL('default', 'index')),
    (H3(XML('<i class="fa fa-credit-card"></i>'
        )),
        0, URL('default', 'withdraw')),
    (H3(XML(
        '<i class="fa fa-magic"></i>'
        )),
        0, URL('more', 'index')),
    (
        #T('Join'),
        H3(XML('<i class="fa fa-user-plus"></i>')),
        0, URL('default', 'join')),
    (H3(XML(
        '<i class="fa fa-money"></i>'
        )),
        0, URL('default', 'currs')),
    ]
if IS_LOCAL:
        response.menu.append((
        #T('About'),
        H3(XML('<i class="fa fa-wrench"></i>')),
        0, URL('admin','default', 'design', args=[request.application])))


lang_curr = session.lang or T.accepted_language
# если текущий язык не ннайден в нашем списке то покажем Англ как текущий
if not LANGS[lang_curr]: lang_curr = 'en'

_lang = LANGS.get(lang_curr, LANGS.get('en', LANGS.get('ru'))) ## dict.keys()[0]
def lang_sel():
    langs = []
    for (n,l) in LANGS.iteritems():
        if lang_curr == n: continue
        vars = request.vars.copy()
        vars['lang'] = n
        langs.append((
                CAT(IMG(_src=URL('static', 'images/flags/' + l[1]), _width=30, _alt=''),
                    ' ',l[0]), False, URL(args=request.args, vars=vars))
              )
    return langs
'''
    return [
        (CAT(IMG(_src=URL('static', 'images/flags/' + _lang[1]), _width=30, _alt=''), ' ', _lang[0]),
            False, None, langs)
        ]
'''
