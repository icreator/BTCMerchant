# -*- coding: utf-8 -*-
if request.is_local:
    recl_bottom = None
else:
    width = IS_MOBILE and '300' or '468'
    recl_a_ads_com = '''
      <center>
        <div>
    <iframe data-aa='76581' src='https://ad.a-ads.com/76581?size=468x60' scrolling='no' style='width:''' +    width +'''px; height:60px; border:0px; padding:0;overflow:hidden' allowtransparency='true' frameborder='0'></iframe>
        <div>
            <a href="//a-ads.com?partner=76581" target="_blank">&#8657; Advertise with Anonymous Ads &#8657;</a>
        </div>
    </center>
    '''
    recl_adbit_co_2 = '''
    <center>
        <div>
            <iframe scrolling="no" frameborder="0" src="//adbit.co/adspace.php?a=L69EKW8CTS8Q5" style="overflow:hidden;width:''' + width + '''px;height:60px;"></iframe>
        </div>
        <div>
            <a href="//adbit.co/?a=Advertise&b=View_Bid&c=L69EKW8CTS8Q5" target="_blank">&#8657; Your Ad Here &#8657;</a>
        </div>
    </center>
        '''

    recl_bottom = [
        '''
            <center>
        <div>
            <iframe scrolling="no" frameborder="0" src="//adbit.co/adspace.php?a=DT97AC6LELUO4" style="overflow:hidden;width:''' + width + '''px;height:60px;"></iframe>
        </div>
        <div>
            <a href="//adbit.co/?a=Advertise&b=View_Bid&c=DT97AC6LELUO4" target="_blank">&#8657; Your Ad Here &#8657;</a>
        </div>
    </center>
        ''',
        recl_a_ads_com
        ]
