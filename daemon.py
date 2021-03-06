#!/usr/bin/python
import socket, sys, os, urllib, urllib2, json, sqlite3, random, imghdr, time, traceback
from time import localtime, strftime
from os.path import join as join_path
import os_specific

scriptDirectory = os.path.dirname(os.path.realpath(__file__))
server_address = ('localhost', 8888)
images_directory = 'pics'

conn, sock, logfile = None, None, None
last = time.time()-3600
#TODO: change schema so no two urls or names can be the same
#db schema   name url liked-default-0 priority-defalut-0 ignore-default-0
# priority is the priority of when you want to see it, it will shows images with priority =0 before, priority=1
# 5 means that you've already displayed it.

#TODO: save images with the correct file extension
#TODO: change os importing, such that you don't need libraries that you don't need.

#requires crontab


(getDesktopImage, setDesktopImage, createCronJobs, asynch_start) = os_specific.load()


# -----------------------------------------------
# ----------------On Startup---------------------
# -----------------------------------------------
def start():
    #connect to db
    global conn, sock, logfile
    logfile = open(scriptDirectory + '/log.log', 'a');
    printAll('Connecting To Pics DB')
    conn = sqlite3.connect(join_path(scriptDirectory, 'desktopPics.db'))
    c = conn.cursor()
    c.execute('create table if not exists data (name text, url text primary key, liked integer default 0, priority integer default 0, ignore integer default 0)')
    conn.commit()
    serversocket = initSocket()

    dir_path = join_path(scriptDirectory, images_directory)
    if not os.path.exists(dir_path):
        printAll("Created Image Directory: ", dir_path)
        os.makedirs(dir_path)
    createCronJobs()

    #start socket

    while True:
        # Wait for a connection
        #TODO: when get info from client, handle it and close connection, wait to accept another
        sock, client_address = serversocket.accept()
        sock.settimeout(None)
        try:
            # Receive the data in small chunks and retransmit it
            data = sock.recv(1024) #YUNO BLOCK!!!!
            log('received "%s"' % data)
            if data == "":
                continue
            handle(data)
        finally:
            # Clean up the connection
            sock.close()



def initSocket():
    serversocket =  socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    printAll('Starting up socket listner on(%s, %s)' % server_address)
    serversocket.bind(server_address)
    serversocket.listen(1)
    return serversocket


#------------------------------------------------
#------------------Utility-----------------------
#------------------------------------------------

def pullPornImages(subreddit):
    #TODO: handle flickr with beautiful soup
    printAll("Pulling from ", subreddit)
    url = 'failed on subreddit url'
    try:
        response = urllib2.urlopen("http://www.reddit.com/r/%s/top/.json?sort=top&t=all" % subreddit)
        data = json.load(response)
        for child in data['data']['children']:
            url = child['data']['url']
            name = child['data']['subreddit_id'] + "-" +  child['data']['id']
            downloadImage(url,name, 1)
    except (urllib2.HTTPError, urllib2.URLError) as e:
        # traceback.format_exc()
        printAll(url)

def pullBingImages():
    printAll('Pulling from Bing image of the day')
    url =  'failed on bing url'
    try:
        response = urllib2.urlopen('http://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=8&mkt=en-US')
        data = json.load(response)
        for image in data['images']:
            url = 'http://www.bing.com' + image['url']
            name =  image['startdate']
            downloadImage(url, name, 0)
    except (urllib2.HTTPError, urllib2.URLError) as e:
        printAll("Exception was thrown", e, url)
        # traceback.format_exc()


def downloadImage(url, name, priority):
    cursor = conn.cursor()
    array = cursor.execute("select url from data where url=?", (url,)).fetchall()
    # we've seen this image before
    if len(array) != 0:
        return
    path = genrate_path(name)
    try:
        urllib.urlretrieve(url, path)
        fileExtension = imghdr.what(path)
        if fileExtension in ['jpg',  'jpeg', 'gif', 'png']:
            os.rename(path, path+'.'+fileExtension)
            cursor.execute("INSERT INTO data (name, url, priority) VALUES (?, ?, ?);",
                (name + '.' + fileExtension, url, priority))
            conn.commit()
        else:
            cursor.execute("INSERT INTO data (name, url, ignore) VALUES (?, ?, ?);",
                (name, url, 1))
            os.unlink(path)
    # except (urllib.error.HTTPError, urllib.error.URLError) as e:
    except Exception as e:
        printAll("Exception was thrown", e, url)
        traceback.format_exc()


def genrate_path(name):
    return join_path(scriptDirectory, images_directory, name)

def log(*args):
    s = ' '.join(args)
    print s
    datetime_prefix = strftime("%Y-%m-%d %H:%M:%S", localtime())
    if args != ('\n',):
        logfile.write("[%s]\t%s\n" % (datetime_prefix, s))
    else:
        logfile.write("\n")
    logfile.flush()

def printAll(*args):
    log(*args)
    s = ' '.join(args)
    if sock != None:
        sock.sendall(s)

# ------------------------------------------------------
# ----------------- Commands From Client----------------
# ------------------------------------------------------
def handle(command):
    global last
    log("\n")
    if command == "thumbsUp":
        thumbsUp(getDesktopImage())
    elif command == "thumbsDown":
        thumbsDown(getDesktopImage())
    elif command == "next":
        next()
    elif command == "dailyUpdate":
        if time.time() - last > 3600:
            printAll("Running dailyUpdate at ", time.time())
            next()
            last = time.time()
        else:
            print "daily update watinging till", 3600-(time.time()-last), "seconds"
    elif command == "quit":
        printAll("closing server")
        sys.exit(0)
    else:
        printAll("%s is not a valid command" % command)
        return
    printAll("success: " + command)


def next():
    pullBingImages()
    for subreddit in ['waterporn', 'fireporn', 'earthporn', 'cloudporn']:
        pullPornImages(subreddit)
    printAll('Done Pulling Images')
    c = conn.cursor()
    array = []
    count = 0
    while len(array) == 0:
        array = c.execute("select name, rowid from data where priority=? and ignore=0", (count,)).fetchall()
        count+=1
    if count > 5:
        printAll("you have no fresh images")
    selected = random.choice(array)
    name, id = selected
    c.execute("update data set priority=5 where rowid=?", (id,))
    conn.commit()
    path = genrate_path(name)
    printAll("changing image")
    setDesktopImage(path)

def thumbsDown(imageName):
    c = conn.cursor()
    c.execute("update data set liked=-1,priority=99 where name=?",(imageName,))
    conn.commit()
    next()

def thumbsUp(imageName):
    c = conn.cursor()
    c.execute("update data set liked=1 where name=?",(imageName,))
    conn.commit()




if __name__ == "__main__":
    start()
