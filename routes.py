# -*- coding: utf-8 -*-

routes_in = (
    # очень много запросов идут на эту иконку почемуто. ответ сервера 400(код ошибки) 50(миллисек?)
    (r'/favicon.ico', r'/bets/static/images/favicon.png'),
    (r'/favicon.png', r'/bets/static/images/favicon.png'),
    (r'/robots.txt', r'/bets/static/robots.txt'),
    (r'/bets/favicon.ico', r'/bets/static/images/favicon.png'),
    (r'/bets/favicon.png', r'/bets/static/images/favicon.png'),
    (r'/bets/robots.txt', r'/bets/static/robots.txt'),
	(r'/bets_dvlp/$anything', r'/bets_dvlp/$anything'), # перенаправляем на ставки
	(r'/bets/$anything', r'/bets/$anything'),
        (r'/$anything', r'/bets/$anything'),
	)


routes_out = [
#    (x, y) for (y, x) in routes_in]
    (r'/bets/static/images/favicon.png', r'/favicon.ico'),
    (r'/bets/static/images/favicon.png', r'/favicon.png'),
    (r'/bets/static/robots.txt', r'/robots.txt'),
    (r'/bets/$anything', r'/$anything'),
    ]

