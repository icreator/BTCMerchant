:rep


rem ..\..\%1 -S %2 -M -R applications/%2/modules/serv_blocks.py -A %3 %4
..\..\%1 -S bets -M -R applications/bets/private/serve.py

timeout /t 10

rem if fail - repeat
goto rep
