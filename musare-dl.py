#!/usr/bin/python3.8

import sys
import getopt
import json
import pymongo
from bson.objectid import ObjectId
import youtube_dl
import ffmpy
import os
import eyed3
from urllib import request
import unicodedata
import re
from PIL import Image
import PIL
from alive_progress import alive_bar

class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

def keys_exists(element, *keys):
    if not isinstance(element, dict):
        raise AttributeError("keys_exists() expects dict as first argument.")
    if len(keys) == 0:
        raise AttributeError("keys_exists() expects at least two arguments, one given.")
    _element = element
    for key in keys:
        try:
            _element = _element[key]
        except:
            return False
    return True

def usage(e=False):
    print(f"""{bcolors.HEADER}Usage{bcolors.ENDC}
    -h,--help | Help
    -p playlistId,--playlist-id=playlistId | Musare Playlist ID
    -P playlistFile,--playlist-file=playlistFile | Musare Playlist JSON file
    -o outputPath,--output=outputPath | Output directory
    -f outputFormat,--format=outputFormat | Format of download, audio or video
    -i downloadImages,--images=downloadImages | Whether to download images, true or false
    --max-songs=maxSongs | Maximum number of songs to download
    --mongo-host=mongoHost | MongoDB Host
    --mongo-port=mongoPort | MongoDB Port
    --mongo-username=mongoUsername | MongoDB Username
    --mongo-password=mongoPassword | MongoDB Password
    --mongo-database=mongoDatabase | MongoDB Database
    """)
    if e:
        sys.exit(2)

def slugify(value):
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^(?!+)\w\s-]", "", value)
    return re.sub(r"[\s]+", "_", value).strip("-_")

mongoSettings = {}
playlistId = None
playlistFile = None
outputDir = os.path.join(os.getcwd(), "")
outputFormat = None
configFile = f"{outputDir}config.json"
downloadImages = True
maxSongs = 0

os.chdir(outputDir)

try:
    opts, args = getopt.getopt(
        sys.argv[1:],
        "p:P:o:f:i:c:h",
        [
            "playlist-id=",
            "playlist-file=",
            "output=",
            "format=",
            "images=",
            "config=",
            "help",
            "max-songs=",
            "mongo-host=",
            "mongo-port=",
            "mongo-username=",
            "mongo-password=",
            "mongo-database="
        ]
    )
except getopt.GetoptError:
    usage(True)

try:
    for opt, arg in opts:
        if opt in ("-c", "--config"):
            configFile = arg
            if not os.path.exists(configFile):
                sys.exit(f"{bcolors.FAIL}Error: Config file does not exist{bcolors.ENDC}")
    if os.path.exists(configFile):
        if os.path.isdir(configFile):
            sys.exit(f"{bcolors.FAIL}Error: Config file is a directory{bcolors.ENDC}")
        with open(configFile, "r") as configJson:
            config = json.load(configJson)
        for var in ["playlistId", "playlistFile", "outputPath", "outputFile", "downloadImages", "maxSongs"]:
            if keys_exists(config, var):
                globals()[var] = config[var]
        for param in ["host", "port", "username", "password", "database"]:
            if not keys_exists(mongoSettings, param) and keys_exists(config, "mongo", param):
                mongoSettings[param] = config["mongo"][param]
        if not keys_exists(mongoSettings, "host"):
            mongoSettings["host"] = "localhost"
        if not keys_exists(mongoSettings, "port"):
            mongoSettings["port"] = 27017
        if not keys_exists(mongoSettings, "username") or not keys_exists(mongoSettings, "password") or not keys_exists(mongoSettings, "database"):
            raise ValueError
except ValueError:
    print(f"{bcolors.FAIL}Error: Mongo username, password and database required{bcolors.ENDC}")
    usage(True)
except:
    sys.exit(f"{bcolors.FAIL}Error loading config.json{bcolors.ENDC}")

for opt, arg in opts:
    if opt in ("-h", "--help"):
        usage(True)
    elif opt in ("-p", "--playlist-id"):
        playlistId = arg
    elif opt in ("-P", "--playlist-file"):
        playlistFile = arg
    elif opt in ("-o", "--output"):
        outputDir = arg
    elif opt in ("-f", "--format"):
        outputFormat = arg
    elif opt in ("-i", "--images"):
        downloadImages = arg
    elif opt in ("-c", "--config"):
        pass
    elif opt == "--max-songs":
        if arg.isdigit() == False:
            sys.exit(f"{bcolors.FAIL}Error: Invalid max-songs, must be int{bcolors.ENDC}")
        maxSongs = arg
    elif opt == "--mongo-host":
        mongoSettings["host"] = arg
    elif opt == "--mongo-port":
        mongoSettings["port"] = arg
    elif opt == "--mongo-username":
        mongoSettings["username"] = arg
    elif opt == "--mongo-password":
        mongoSettings["password"] = arg
    elif opt == "--mongo-database":
        mongoSettings["database"] = arg
    else:
        usage(True)

if not playlistId and not playlistFile:
    print(f"{bcolors.FAIL}Error: Playlist ID or Playlist File need to be specified{bcolors.ENDC}")
    usage(True)
if playlistId and playlistFile:
    print(f"{bcolors.FAIL}Error: Playlist ID and Playlist File can not be used at the same time{bcolors.ENDC}")
    usage(True)
if playlistId and len(playlistId) != 24:
    sys.exit(f"{bcolors.FAIL}Error: Invalid Musare Playlist ID{bcolors.ENDC}")
if playlistFile:
    if not os.path.exists(playlistFile):
        sys.exit(f"{bcolors.FAIL}Error: Musare Playlist File does not exist{bcolors.ENDC}")
    if os.path.isdir(playlistFile):
        sys.exit(f"{bcolors.FAIL}Error: Musare Playlist File is a directory{bcolors.ENDC}")
if os.path.exists(outputDir):
    if not os.path.isdir(outputDir):
        sys.exit(f"{bcolors.FAIL}Error: Output path is not a directory{bcolors.ENDC}")
    outputDir = os.path.join(outputDir, "")
else:
    sys.exit(f"{bcolors.FAIL}Error: Output directory does not exist{bcolors.ENDC}")
if outputFormat:
    outputFormat = outputFormat.lower()
    if outputFormat != "audio" and outputFormat != "video":
        sys.exit(f"{bcolors.FAIL}Error: Invalid format, audio or video only{bcolors.ENDC}")
else:
    outputFormat = "audio"
if str(downloadImages).lower() == "true":
    downloadImages = True
elif str(downloadImages).lower() == "false":
    downloadImages = False
else:
    sys.exit(f"{bcolors.FAIL}Error: Invalid images, must be True or False{bcolors.ENDC}")
maxSongs = int(maxSongs)

if playlistId and not playlistFile:
    try:
        mongo = pymongo.MongoClient(
            host=mongoSettings["host"],
            port=int(mongoSettings["port"]),
            username=mongoSettings["username"],
            password=mongoSettings["password"],
            authSource=mongoSettings["database"]
        )
        mydb = mongo[mongoSettings["database"]]

        songs = []
        for playlist in mydb["playlists"].find({ "_id": ObjectId(playlistId) }, { "songs._id" }):
            for song in playlist["songs"]:
                songs.append(song["_id"])
        songsCount = mydb["songs"].count_documents({ "_id": { "$in": songs } })
        songs = mydb["songs"].find({ "_id": { "$in": songs } })
    except:
        sys.exit(f"{bcolors.FAIL}Error: Could not load songs from Mongo{bcolors.ENDC}")
elif not playlistId and playlistFile:
    try:
        with open(playlistFile, "r") as playlistJson:
            songs = json.load(playlistJson)
        songs = songs["playlist"]["songs"]
        songsCount = len(songs)
    except:
        sys.exit(f"{bcolors.FAIL}Error: Could not load songs from playlist JSON file{bcolors.ENDC}")

if not os.access(outputDir, os.W_OK):
    sys.exit(f"{bcolors.FAIL}Error: Unable to write to output directory{bcolors.ENDC}")
if os.getcwd() != outputDir:
    os.chdir(outputDir)
if downloadImages and not os.path.exists("images"):
    os.makedirs("images")

i = 0
completeSongs = []
failedSongs = []
if maxSongs > 0 and songsCount > maxSongs:
    songsCount = maxSongs
with alive_bar(songsCount, title=f"{bcolors.BOLD}{bcolors.OKCYAN}musare-dl{bcolors.ENDC}") as bar:
    for song in songs:
        i = i + 1
        if maxSongs != 0 and i > maxSongs:
            i = i - 1
            break
        try:
            bar.text(f"{bcolors.OKBLUE}Downloading ({song['_id']}) {','.join(song['artists'])} - {song['title']}..{bcolors.ENDC}")
            ydl_opts = {
                "outtmpl": f"{song['_id']}.tmp",
                "quiet": True,
                "no_warnings": True
            }
            if outputFormat == "audio":
                outputExtension = "mp3"
                ydl_opts["format"] = "bestaudio[ext=m4a]"
            elif outputFormat == "video":
                outputExtension = "mp4"
                ydl_opts["format"] = "best[height<=1080]/bestaudio"
            ffmpegOpts = ["-hide_banner", "-loglevel", "error"]
            if keys_exists(song, "skipDuration") and keys_exists(song, "duration"):
                ffmpegOpts.append("-ss")
                ffmpegOpts.append(str(song["skipDuration"]))
                ffmpegOpts.append("-t")
                ffmpegOpts.append(str(song["duration"]))
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={song['youtubeId']}"])
            bar.text(f"{bcolors.OKBLUE}Converting ({song['_id']}) {','.join(song['artists'])} - {song['title']}..{bcolors.ENDC}")
            ff = ffmpy.FFmpeg(
                inputs={ f"{song['_id']}.tmp": None },
                outputs={ f"{song['_id']}.{outputExtension}": ffmpegOpts }
            )
            ff.run()
            os.remove(f"{song['_id']}.tmp")
            if outputFormat == "audio":
                track = eyed3.load(f"{song['_id']}.{outputExtension}")
                track.tag.artist = ";".join(song["artists"])
                track.tag.title = str(song["title"])
                if keys_exists(song, "discogs", "album", "title"):
                    track.tag.album = str(song["discogs"]["album"]["title"])
            fileName = slugify(f"{'+'.join(song['artists'])}-{song['title']}-{song['_id']}")
            bar.text(f"{bcolors.OKBLUE}Downloading Images for ({song['_id']}) {','.join(song['artists'])} - {song['title']}..{bcolors.ENDC}")
            if downloadImages:
                try:
                    imgRequest = request.Request(
                        song["thumbnail"],
                        headers={
                            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36"
                        }
                    )
                    img = Image.open(request.urlopen(imgRequest))
                    img.save(f"images/{fileName}.jpg", "JPEG")
                    if outputFormat == "audio":
                        thumb = img.resize((32, 32), Image.Resampling.LANCZOS)
                        thumb.save(f"images/{fileName}.thumb.jpg", "JPEG")
                        imgData = open(f"images/{fileName}.jpg", "rb").read()
                        thumbData = open(f"images/{fileName}.thumb.jpg", "rb").read()
                        track.tag.images.set(1, thumbData, "image/jpeg", u"icon")
                        track.tag.images.set(3, imgData, "image/jpeg", u"cover")
                except:
                    print(f"{bcolors.FAIL}Error downloading album art for ({song['_id']}) {','.join(song['artists'])} - {song['title']}, skipping.{bcolors.ENDC}")
            if outputFormat == "audio":
                track.tag.save()
            os.rename(f"{song['_id']}.{outputExtension}", f"{fileName}.{outputExtension}")
            completeSongs.append(str(song["_id"]))
            print(f"{bcolors.OKGREEN}Downloaded ({song['_id']}) {','.join(song['artists'])} - {song['title']}{bcolors.ENDC}")
        except KeyboardInterrupt:
            print(f"{bcolors.FAIL}Cancelled downloads{bcolors.ENDC}")
            break
        except:
            failedSongs.append(str(song["_id"]))
            print(f"{bcolors.FAIL}Error downloading ({song['_id']}) {','.join(song['artists'])} - {song['title']}, skipping.{bcolors.ENDC}")
        bar()
if len(failedSongs) > 0:
    print(f"\n{bcolors.FAIL}Failed Songs ({len(failedSongs)}): {', '.join(failedSongs)}{bcolors.ENDC}")
