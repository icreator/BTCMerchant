# coding: utf8
# попробовать что-либо вида
def index():
    session.forget(response)
    v = {}
    #for r in db(db.news).select(orderby=~db.news.on_create, limitby=(0, 100)):
    #    v[ r.head] = r.body
    #rec
    #response.vars = { 'r': v}
    #print response._vars
    rs=db(db.news).select(orderby=~db.news.on_create, limitby=(0, 100))
    
    return dict(rs=rs, message="")
