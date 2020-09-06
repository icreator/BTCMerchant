from gluon.storage import Storage
## app configuration made easy. Look inside private/appconfig.ini
from gluon.contrib.appconfig import AppConfig
## once in production, remove reload=True to gain full speed
myconf = AppConfig(reload=True)

if request.ajax:
    pass
else:
    LANGS = myconf['langs']
    # if request to change LANG
    lang = request.vars.lang
    if lang:
        if lang != session.lang and lang in LANGS:
            session.lang = lang
        request.vars.pop('lang')
        #print '0.py - lang -> %s' % session.lang
        redirect(URL( args = request.args, vars = request.vars))

    alerts = myconf['alerts']
    if alerts and 'show' in alerts:
        #print alerts
        response.alert = alerts.get(T.accepted_language, 'en')

# force LANG
if session.lang and T.accepted_language != session.lang:
    T.force(session.lang)

IS_MOBILE = request.user_agent().is_mobile
IS_LOCAL = request.is_local
DEVELOP = myconf.take('app.develop', cast=bool)
SETS = Storage(myconf.take('sets'))
#SETS.title = CAT(XML(SETS.title))
#SETS.subtitle = CAT(XML(SETS.subtitle))

if request.ajax:
    pass
else:
    if not IS_MOBILE:
        response.logo = A(IMG(_src=URL('static','images/logo_bets2m.png'), _width=270),
                  _href=URL('default', 'index'), _class='pull-left', _id='logo')
    else:
        response.logo = A(IMG(_src=URL('static','images/logo_bets2mm.png'), _width1=70),
                  _href=URL('default', 'index'), _class='pull-left', _id='logo')
