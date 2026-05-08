@echo off
call .\venv\Scripts\activate.bat
python import_base_data.py basedata.xlsx
call deactivate.bat