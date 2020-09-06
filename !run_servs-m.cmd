start !clear_sessions.cmd
start !clear_errors.cmd

set pp=%CD%
cd ..\wallets--shop
start !!start_wallets_unote.cmd
cd %pp%


set prog=web2py.py
set app=app=lite_cash
set not_local=True
set interval=10
set interval30=10
set interval60=60

timeout /t 10
start serv_blocks.cmd %prog% %app% %not_local% %interval%
timeout /t 3
start serv_notes.cmd %prog% %app% %not_local% %interval30%

timeout /t 3
start serv_bets.cmd %prog%

:rep
..\..\%prog% -S %app% -M -R applications/%app%/modules/serv_rates.py -A %not_local% %interval60%


timeout /t 20
goto rep

pause