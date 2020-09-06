:rep
..\..\%1 -S %2 -M -R applications/%2/modules/serv_blocks.py -A %3 %4

timeout /t 100

rem if fail - repeat
goto rep
