pyinstaller ^
upload_to_youtube.py ^
--name="uploader" ^
--paths=env\Lib\site-packages ^
--add-data="youtube-api-creds-web.json;." ^
--icon=app.ico ^
--copy-metadata flask ^
--hidden-import=moviepy ^
--hidden-import=numpy ^
--hidden-import=apiclient ^
--hidden-import=oauth2client ^
--hidden-import=httplib2 ^
--noconfirm ^
--onefile ^