from distutils.command.upload import upload
import os, glob, json, sys

from moviepy.editor import VideoFileClip, concatenate_videoclips
from pymediainfo import MediaInfo
import datetime
from time import sleep
# import sibling modules sys hack
# sys.path.append('..')
# from upload_to_youtube import upload_video

CURRENT_STATUS_MSG = 'ready'
ESTIMATED_VIDEO_DURATION = (0, 0, 0) # tuple representing hours, minutes, seconds.
VIDEO_DESCRIPTION = '' # Will be auto-generated and based on the clips filenames.

from enum import Enum

class TWITCH_PERIOD(Enum):
    LAST_DAY   = 'last_day'
    LAST_WEEK  = 'last_week'
    LAST_MONTH = 'last_month'
    LAST_YEAR  = 'last_year'
    ALL_TIME   = 'all_time'


def printBanner(label):
    print('\n' + '*' * len(label))
    print(label)
    print('*' * len(label) + '\n')


def get_clips_without_compilation_video():
    clips = glob.glob('clips/*.mp4')
    try:
        clips.remove('clips\\compilation.mp4')
    except ValueError:
        pass
    return clips


"""
   _____ _           _          _          __  __ 
  |  ___| | __ _ ___| | __  ___| |_ _   _ / _|/ _|
  | |_  | |/ _` / __| |/ / / __| __| | | | |_| |_ 
  |  _| | | (_| \__ \   <  \__ \ |_| |_| |  _|  _|
  |_|   |_|\__,_|___/_|\_\ |___/\__|\__,_|_| |_|  
"""

def __notify_flask_status(msg):
    global CURRENT_STATUS_MSG
    CURRENT_STATUS_MSG = msg
    return CURRENT_STATUS_MSG
    print(msg)

def get_current_status_msg():
    """
    Returns the current status message. Intended to be called via AJAX and routed inside an API route in Flask."""
    return CURRENT_STATUS_MSG

def __notify_flask_video_duration(duration):
    global ESTIMATED_VIDEO_DURATION
    ESTIMATED_VIDEO_DURATION = duration

def get_estimated_video_duration():
    """
    Returns a tuple representing hours, minutes, seconds. Intended to be called via AJAX and routed inside an API route in Flask."""
    return ESTIMATED_VIDEO_DURATION

"""
   _____          _ _       _           _          __  __ 
  |_   _|_      _(_) |_ ___| |__    ___| |_ _   _ / _|/ _|
    | | \ \ /\ / / | __/ __| '_ \  / __| __| | | | |_| |_ 
    | |  \ V  V /| | || (__| | | | \__ \ |_| |_| |  _|  _|
    |_|   \_/\_/ |_|\__\___|_| |_| |___/\__|\__,_|_| |_|  
                                                          
"""

def download_clips(channel, limit=5, period='last_week'):
    if not os.path.exists('clips'):
        os.mkdir('clips')
    # change directory to the clips folder
    os.chdir('clips')
    os.system(f'..\\twitch-dl.exe clips {channel} -l {limit} --download --period {period}')
    # change directory back to the root folder
    os.chdir('..')

def twitch_list_clips(channel: str, limit: int, period: str, getJSON: bool, sortByViews=True):
    """
    resulting JSON contains these keys:
    -------------------------------------------
    id
    slug
    title
    createdAt
    viewCount
    durationSeconds
    url
    videoQualities
    game
    broadcaster
    """
    if not getJSON:
        return os.popen(f'.\\twitch-dl.exe clips {channel} --l {limit} --period {period}').read()
    j = json.loads(os.popen(f'.\\twitch-dl.exe clips {channel} --l {limit} --period {period} --json').read())
    if sortByViews:
        j.sort(key=lambda x: x['viewCount'], reverse=True)
    return j
    
def twitch_download_single_mediafile(identifier: str):
    """
    Downloads a single media file from twitch.tv.
    Identifier: Video ID | Clip slug | URI

    e.g.
    twitch-dl download 221837124
    twitch-dl download https://www.twitch.tv/videos/221837124

    +=================================================================================+
    +                       TEMPLATING VARIABLES                                      +
    +=================================================================================+
    | Placeholder     | Description                  | Example                        |
    |-----------------|------------------------------|--------------------------------|
    | {id}            | Video ID                     | 1255522958                     |
    | {title}         | Video title                  | Dark Souls 3 First playthrough |
    | {title_slug}    | Slugified video title        | dark_souls_3_first_playthrough |
    | {datetime}      | Video date and time          | 2022-01-07T04:00:27Z           |
    | {date}          | Video date                   | 2022-01-07                     |
    | {time}          | Video time                   | 04:00:27Z                      |
    | {channel}       | Channel name                 | KatLink                        |
    | {channel_login} | Channel login                | katlink                        |
    | {format}        | File extension, see --format | mkv                            |
    | {game}          | Game name                    | Dark Souls III                 |
    | {game_slug}     | Slugified game name          | dark_souls_iii                 |
    | {slug}          | Clip slug (clips only)       | AbrasivePlacidCatDxAbomb       |

    ...
    """
    os.system(f'.\\twitch-dl.exe download {identifier} --quality "source"' + ' --output "clips\\{channel_login}-{title}.{format}"')


def twitch_download_clips_formatted(channel: str, limit: int, period: str):
    """
    Downloads a list of clips from twitch.tv.
    Returns a list of dictionaries containing the following keys:
    -------------------------------------------
    id
    slug
    title
    createdAt
    viewCount
    durationSeconds
    url
    videoQualities
    game
    broadcaster
    """
    __notify_flask_status('starting clips download')
    clips_metadata = twitch_list_clips(channel, limit, period, getJSON=True)
    for clip in clips_metadata:
        __notify_flask_status(f'downloading clip {clip["title"]} by {clip["broadcaster"]["displayName"]}')
        twitch_download_single_mediafile(clip['url'])

def twitch_get_best_clip_of_yesterday_from_multiple_channels(channels: list, num_of_clips_per_channel: int, shouldDownload: bool):
    clips_to_be_processed = []
    for channel in channels:
        channel_clips = twitch_list_clips(channel, limit=num_of_clips_per_channel, period='last_day', getJSON=True)
        clip_with_highest_view_count_in_specified_period = max(channel_clips, key=lambda x: x['viewCount'])
        clips_to_be_processed.append(clip_with_highest_view_count_in_specified_period)
    if shouldDownload:
        for clip in clips_to_be_processed:
            twitch_download_single_mediafile(clip['url'])
        move_clips_to_clips_folder()
    return clips_to_be_processed

def get_most_loved_channels_by_category(category: str, num_of_channels: int):
    num_of_channels = 5 # hard-cap for now.
    if category.lower() == 'Apex Legends'.lower():
        return ['sweetdreams', 'daltoosh', 'tsm_imperialhal', 'mande', 'enoch', 'shivfps', 'loustreams', 'nickmercs']


"""
   _____ _ _                     _                       _          __  __ 
  |  ___(_) | ___  ___ _   _ ___| |_ ___ _ __ ___    ___| |_ _   _ / _|/ _|
  | |_  | | |/ _ \/ __| | | / __| __/ _ \ '_ ` _ \  / __| __| | | | |_| |_ 
  |  _| | | |  __/\__ \ |_| \__ \ ||  __/ | | | | | \__ \ |_| |_| |  _|  _|
  |_|   |_|_|\___||___/\__, |___/\__\___|_| |_| |_| |___/\__|\__,_|_| |_|  
                       |___/                                               
"""

def move_clips_to_clips_folder():
    # move clips to designated folder as the twitch-dl CLI does not do this / or I'm too lazy to look it up.
    if not os.path.exists('clips'):
        os.mkdir('clips')
    os.system('mv *.mp4 clips')

def remove_source_clips():
    clips = get_clips_without_compilation_video()
    for clip in clips:
        os.remove(clip)

def get_clip_duration_in_hours_minutes_seconds(clip):
    info = MediaInfo.parse(clip).tracks[0]
    duration = info.other_duration[4] # hh:mm:ss:ms
    duration = duration.replace(';', ':')
    hours, minutes, seconds, _ = duration.split(':')
    return (int(hours), int(minutes), int(seconds))

def get_total_clips_duration_in_hours_minutes_seconds(clips: list):
    total_hours = 0
    total_minutes = 0
    total_seconds = 0
    for clip in clips:
        clip_duration  = get_clip_duration_in_hours_minutes_seconds(clip)
        total_hours   += clip_duration[0]
        total_minutes += clip_duration[1]
        total_seconds += clip_duration[2]
    return (total_hours, total_minutes, total_seconds)

def make_upload_ready_compilation(keep_source_clips=False):
    __notify_flask_status('merging clips into compilation video (this might take several minutes)')
    def _ffmpeg_implementation():
        with open('clips.txt', 'w') as output:
            for clip in clips:
                output.write("file '" + clip + "'\n")
        # make a compilation of all clips in the clips folder
        # os.system('ffmpeg -f concat -safe 0 -vsync 2 -i clips.txt clips\\compilation.mp4 ')
        os.system('ffmpeg -f concat -safe 0 -vsync 2 -i clips.txt -c copy clips\\compilation.mp4 -y') # BLAZINGLY FAST
        # os.system('ffmpeg -f concat -safe 0 -i clips.txt -vf mpdecimate -c:a copy -vsync vfr clips\\compilation.mp4 -y') # SLOW

    def _moviepy_implementation():
        concatinated = concatenate_videoclips([VideoFileClip(v) for v in clips])
        concatinated.write_videofile('compilation' + '.mp4',
                        codec='libx264',
                        verbose=False,
                        logger=None,
                        threads=32)
        os.system('mv compilation.mp4 clips')

    clips = get_clips_without_compilation_video()
    __notify_flask_video_duration(get_total_clips_duration_in_hours_minutes_seconds(clips)) # notify flask app
    # files.sort(key=lambda x: os.path.getctime(x))
    # CHOOSE WHICH IMPLEMENTATION TO USE --------------------------------
    # _ffmpeg_implementation()
    _moviepy_implementation()

    if not keep_source_clips:
        remove_source_clips()
    __notify_flask_status('merging complete')
    __notify_flask_status('compilation video ready for upload')
    

def make_vid_list():
    files = list(filter(os.path.isfile, glob.glob(os.path.join(os.getcwd() + '\\clips', '*.mp4'))))
    files.sort(key=lambda x: os.path.getctime(x))
    print(files)

    # Write list to text file that ffmpeg reads next.
    with open('clips.txt', 'w') as output:
        for file in files:
            output.write("file '" + file + "'\n")
        output.close()

    # Run ffmpeg to concatenate the .mp4 files.
    # os.system('ffmpeg -f concat -safe 0 -i files.txt merged.mp4')

    # Delete the text file.
    # os.remove('files.txt')

def get_credits_for_clips():
    video_description_head = """"""
    video_description_tail = """


    
#ApexHighlights #ApexLegends #Compilation"""

    credits = []
    # get filenames in clips folder without the path
    clips = get_clips_without_compilation_video()
    accumulative_duration = datetime.timedelta(0)
    for clip in clips: # NOTE: TEMPORARY. NEEDED UNTIL MAIN CLIPS DOWNLOAD FUNCTION SUPPORTS FORMATTING.
        try:
            channel, title = clip.split('-')
        except ValueError:
            channel = clip
            title = clip
        channel = channel.replace('clips\\', '')
        title = title.replace('.mp4', '')
        hours, minutes, seconds = get_clip_duration_in_hours_minutes_seconds(clip)
        duration = datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)
        accumulative_duration += duration
        if clip == clips[0]:
            credits.append(dict(channel=channel, title=title, duration=duration, accumulative_duration=datetime.timedelta(0)))
        else:
            credits.append(dict(channel=channel, title=title, duration=duration, accumulative_duration=accumulative_duration-duration + datetime.timedelta(seconds=1))) # add grace time of one sec for smoother experience while playing back.
    # print(credits)
    def _template(creditDict):
        return f"""{credit['channel']} - {credit['title']}: {credit['accumulative_duration']} (https://www.twitch.tv/{credit['channel']})"""

    def _extended_template(creditDict): # NOTE: not implementable yet. Blocked by some sort of linktree scraper or something.
        return f"""channel
YOUTUBE ▰ https://bit.ly/Toosh_YT
TWITCH ▰ http://bit.ly/Daltoosh_Twitch
TWITTER ▰ http://bit.ly/Daltoosh_Twitter
INSTA ▰ http://bit.ly/Daltoosh_Insta"""
    # write credits to text file
    with open('clips\\credits.txt', 'w') as output:
        output.write(video_description_head)
        for credit in credits:
            output.write(_template(credit) + '\n')
        # append random str to end of file
        output.write(video_description_tail)
        output.close()

    final_output = ''
    final_output += video_description_head
    for credit in credits:
        final_output += _template(credit) + '\n'
    final_output += video_description_tail
    return final_output
        
"""
  __   __         _____      _                _          __  __ 
  \ \ / /__  _   |_   _|   _| |__   ___   ___| |_ _   _ / _|/ _|
   \ V / _ \| | | || || | | | '_ \ / _ \ / __| __| | | | |_| |_ 
    | | (_) | |_| || || |_| | |_) |  __/ \__ \ |_| |_| |  _|  _|
    |_|\___/ \__,_||_| \__,_|_.__/ \___| |___/\__|\__,_|_| |_|  
"""

# LEGACY CODE
# ---------------------------------------------------------------------------------------------------------------------
# def run_upload_to_youtube_script():
#     # run the upload script batch file
#     os.system('upload_to_youtube.bat')

# def run_uploader_script():
#     # USE THIS FUNCTION WHEN RUNNING EXE. TEMPORARY. WILL BE OBSOLETE ONCE YOUTUBE UPLOAD SCRIPT HAS BEEN CUSTOMIZED AND TURNED INTO PROGRAMMATIC SCRIPT.
#     command = f"""\.uploader.exe --title="TEST" ^
# --description="TEST" ^
# --keywords="Apex Legends, Apex, Apex Legends Clips" ^
# --category="22" ^
# --privacyStatus="private"""



"""
 
  __     ___     _                                  _               _             _      
  \ \   / (_) __| | ___  ___     _____   _____ _ __| | __ _ _   _  | | ___   __ _(_) ___ 
   \ \ / /| |/ _` |/ _ \/ _ \   / _ \ \ / / _ \ '__| |/ _` | | | | | |/ _ \ / _` | |/ __|
    \ V / | | (_| |  __/ (_) | | (_) \ V /  __/ |  | | (_| | |_| | | | (_) | (_| | | (__ 
     \_/  |_|\__,_|\___|\___/   \___/ \_/ \___|_|  |_|\__,_|\__, | |_|\___/ \__, |_|\___|
                                                            |___/           |___/        
 
"""

from PIL import Image, ImageDraw, ImageFont
import ffmpeg
import os

def makeCreditImage(displayMsg):
    width = 512
    height = 100
    message = "© " + displayMsg
    message = message.upper()
    fill_color = (255, 255, 255)
    stroke_color = (0, 0, 0, 200) # RGBA
    stroke_width = 2
    fontSize = 48
    font = ImageFont.truetype("AGENCYB.ttf", size=fontSize)
    img = Image.new('RGBA', (width, height), (255, 0, 0, 0))
    imgDraw = ImageDraw.Draw(img)
    textWidth, textHeight = imgDraw.textsize(message, font=font)
    # imgDraw.text((0, 0), message, font=font, fill=(255, 255, 255))
    imgDraw.text((50, 10), message, font=font, fill=fill_color, stroke_width=stroke_width, stroke_fill=stroke_color)
    # img.show("")
    img.save('credit.png')

def superimposeCreditImageOntoVideoClip(clip):
    # main = ffmpeg.input(clip)
    # creditTextImage = ffmpeg.input('credit.png')
    # (
    #     ffmpeg
    #     .filter([main, creditTextImage], 'overlay', 10, 10)
    #     .output('out.mp4')
    #     .run(overwrite_output=True)
    # )
# overlay=W-w:H-h <-- use this instead of 25:25 to put to bottom right corner.
    os.system(f"""ffmpeg -i test.mp4 -i credit.png -filter_complex "[0:v][1:v] overlay=25:25:enable='between(t,0)'" \
-pix_fmt yuv420p -c:a copy -safe 0 output.mp4 -y""")

"""
    ____                      _      _          __ _                   
   / ___|___  _ __ ___  _ __ | | ___| |_ ___   / _| | _____      _____ 
  | |   / _ \| '_ ` _ \| '_ \| |/ _ \ __/ _ \ | |_| |/ _ \ \ /\ / / __|
  | |__| (_) | | | | | | |_) | |  __/ ||  __/ |  _| | (_) \ V  V /\__ \
   \____\___/|_| |_| |_| .__/|_|\___|\__\___| |_| |_|\___/ \_/\_/ |___/
                       |_|                                             
"""

def upload_to_youtube():
    __notify_flask_status('uploading to youtube ...')
    month = datetime.datetime.now().strftime('%B')
    year = datetime.datetime.now().strftime('%Y')
    os.system(make_youtube_upload_command(title=f'Apex Legends Twitch Clips Highlights - {month} {year}', description=get_credits_for_clips()))
    __notify_flask_status('upload to youtube complete')

def make_youtube_upload_command(title='test', description='test'):
    return """python -m upload_to_youtube --file="clips\\compilation.mp4" ^
--title="{title}" ^
--description="{description}" ^
--keywords="Apex Legends, Apex, Apex Legends Clips" ^
--category="22" ^
--privacyStatus="private"""

def upload_to_youtube(title='test', description='test'):
    os.system(make_youtube_upload_command(title, description))

def simple_do_all(channel: str, period='last_day'):
    twitch_download_clips_formatted(channel=channel, limit=3, period=period)
    credits = get_credits_for_clips()
    __notify_flask_status('video credits generated.')
    make_upload_ready_compilation(keep_source_clips=False)
    os.system('explorer clips')

def simple_multi_channel_do_all(channels: list):
    channels = get_most_loved_channels_by_category('Apex Legends', 5)
    __notify_flask_status('starting clips download')
    twitch_get_best_clip_of_yesterday_from_multiple_channels(channels, 3, True)
    __notify_flask_status('merging clips into compilation video (this might take several minutes)')
    make_upload_ready_compilation()
    __notify_flask_status('compilation video ready for upload')
    __notify_flask_status('upload to youtube in progress')
    # run_upload_to_youtube_script()
    month = datetime.datetime.now().strftime('%B')
    year = datetime.datetime.now().strftime('%Y')
    os.system(make_youtube_upload_command(title=f'Apex Legends Twitch Clips Highlights - {month} {year}', description=get_credits_for_clips()))
    __notify_flask_status('upload to youtube complete')

if '__main__' == __name__:
    # example channels:
        # daltoosh
        # sweetdreams
    # simple_do_all('sweetdreams')
    #  download_clips('sweetdreams', limit=2, period='last_day')
    # twitch_get_best_clip_of_yesterday_from_multiple_channels(['sweetdreams', 'daltoosh'], num_of_clips_per_channel=1, shouldDownload=True)
    # simple_multi_channel_do_all(get_most_loved_channels_by_category('Apex Legends', 3))
    # print keys of data_model
    # remove_source_clips()
    # os.system('.\\twitch-dl.exe clips sweetdreams -l 2 --period "last_day" --download')
    # os.system(make_youtube_upload_command())
    # pass

    # channels = get_most_loved_channels_by_category('Apex Legends', 5)
    # twitch_get_best_clip_of_yesterday_from_multiple_channels(channels, 3, True)
    # move_clips_to_clips_folder()
    # credits = get_credits_for_clips()
    # make_upload_ready_compilation(keep_source_clips=False)
    # upload_to_youtube(title='Apex Legends Twitch Clips Highlights', description=credits)
    
    simple_do_all('daltoosh')