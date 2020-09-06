:rep
..\..\%1 -S %2 -M -R applications/%2/modules/serv_notes.py -A %3 %4

timeout /t 50

rem if fail - repeat
goto rep
