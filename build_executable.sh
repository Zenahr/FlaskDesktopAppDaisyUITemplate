pyinstaller --name="CPU-Meater" --onefile --paths=env\Lib\site-packages --add-data="static;static" --add-data="templates;templates" app.py --noconsole --icon=app.ico