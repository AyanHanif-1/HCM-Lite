@echo off
setlocal
if not exist hcm_env (
  py -3.11 -m venv hcm_env
)
call hcm_env\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if "%ADMIN_EMAIL%"=="" set ADMIN_EMAIL=admin@hcm.local
if "%ADMIN_PASSWORD%"=="" set ADMIN_PASSWORD=ChangeThisStrongPassword123!
streamlit run app.py
