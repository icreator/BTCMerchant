# coding: utf8
# try something like
def index():
    return dict(f='')

    f = SQLFORM(db.dealers,
        keepvalues=True,
        )
    #my_extra_element = TR(LABEL('I agree to the terms and conditions'),                       INPUT(_name='agree',value=True,_type='checkbox'))
    my_extra_element = TR(LABEL('BTC'), INPUT(_name='BTC',value='',_type='text'))
    f[0].insert(-1,my_extra_element)
    my_extra_element = TR(LABEL('LTC'), INPUT(_name='BTC',value='',_type='text'))
    f[0].insert(-1,my_extra_element)

    if f.process(keepvalues=True).accepted:
        response.flash = T('Добро пожаловать в команду!')

    return locals()
