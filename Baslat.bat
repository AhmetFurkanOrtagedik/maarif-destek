@echo off
echo Maarif Modeli Destek Araci Baslatiliyor...
echo Gerekli kutuphaneler kontrol ediliyor...
py -m pip install -r requirements.txt
echo.
echo Sunucu baslatiliyor... Lutfen tarayicinizdan http://127.0.0.1:5000 adresine gidin.
py app.py
pause
