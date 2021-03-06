import os
from sys import platform
from os.path import join as join_path
from subprocess import Popen, PIPE
scriptDirectory = os.path.dirname(os.path.realpath(__file__))

def load():

	if platform == "darwin":
		print "Darwin os detected"
		luanchdPath = os.path.expanduser("~/Library/LaunchAgents")
		#----------------------------------------------
		#-----------------MAC--------------------------
		#----------------------------------------------
		ClientXML = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>desktopChanger.client</string>
	<key>ProgramArguments</key>
	<array>
		<string>%s</string>
		<string>dailyUpdate</string>
	</array>
	<key>StartInterval</key>
	<integer>86400</integer>
</dict>
</plist>'''

		ServerXML = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>desktopChanger.server</string>
	<key>ProgramArguments</key>
	<array>
		<string>%s</string>
	</array>
	<key>RunAtLoad</key>
	<true/>
</dict>
</plist>'''

		MAC_SET_SCRIPT = '''/usr/bin/sqlite3 /Users/G/Library/Application\ Support/Dock/desktoppicture.db<<END
UPDATE data SET value="%s" WHERE ROWID=2;
END
killall Dock'''

		MAC_GET_COMMAND= ['/usr/bin/sqlite3', '/Users/G/Library/Application Support/Dock/desktoppicture.db', 'select * from data where rowid=2']

		def mac_setDesktopImage(imagePath):
			Popen(MAC_SET_SCRIPT%imagePath, shell=True)

		def mac_getDesktopImage():
			p = Popen(MAC_GET_COMMAND, stdin=PIPE, stdout=PIPE, stderr=PIPE)
			uri, _ =  p.communicate()
			name = uri.rstrip().split("/")[-1]
			return name

		def mac_createCronJobs():
			clientPath = join_path(luanchdPath, "DesktopChangerClient.plist")
			serverPath = join_path(luanchdPath, "DesktopChangerServer.plist")
			if not os.path.exists(clientPath):
				print "Creating Client Agent"
				with open(clientPath, 'w') as client:
					client.write(ClientXML % join_path(scriptDirectory, "client.py"))
				os.chmod(clientPath, 0644)
			if not os.path.exists(serverPath):
				print "Creating Server Agent"
				with open(serverPath, 'w') as client:
					client.write(ServerXML % join_path(scriptDirectory, "daemon.py"))
				os.chmod(serverPath, 0644)
			Popen(['launchctl','load', clientPath])

		def mac_async_start():
			# make sure the neccisary plist are there
			mac_createCronJobs()
			serverPath = join_path(luanchdPath, "DesktopChangerServer.plist")
			Popen(['launchctl', 'load', serverPath])



		return (mac_getDesktopImage, mac_setDesktopImage, mac_createCronJobs, mac_async_start)

		#----------------------------------------------
		#-----------------WIN--------------------------
		#----------------------------------------------
	elif platform == "win32":
		print "Windows OS detected"
		import ctypes as windows_functions

		def windows_setDesktopImage(imagePath):
			lastImage = imagePath
			SPI_SETDESKWALLPAPER = 20
			windows_functions.windll.user32.SystemParametersInfoA(SPI_SETDESKWALLPAPER, 0, str(imagePath) , 0)

		def windows_getDesktopImage():
			return ""

		def windows_createCronJobs():
			if not os.path.exists(join_path(scriptDirectory, 'client.bat')):
				print "Generating client.bat, please schedule a daily task for this batch file"
				with open('client.bat', 'w') as f:
					f.write("python "+join_path(scriptDirectory, 'client.py') +" dailyUpdate")
			if not os.path.exists(join_path(scriptDirectory, 'daemon.bat')):
				print "Generating daemon.bat, please schedule a task to run on boot for this batch file"
				with open('daemon.bat', 'w') as f:
					f.write("start /B python "+join_path(scriptDirectory, 'client.py') +" dailyUpdate")

		def windows_async_start():
			pass

		return (windows_getDesktopImage, windows_setDesktopImage, windows_createCronJobs, windows_async_start)

		#----------------------------------------------
		#-----------------Linux------------------------
		#----------------------------------------------
	elif platform == "linux" or platform == "linux2":
		print "linux os detected"
		from crontab import CronTab

		def linux_getCurrentImageName():
			command ="gsettings get org.gnome.desktop.background picture-uri".split(" ")
			p = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
			uri, _ =  p.communicate()
			name = uri.rstrip().split("/")[-1][:-1]
			return name
			#uri is of the form file:///path/to/file

		def linux_changeDesktopImage(imagePath):
			command = "gsettings set org.gnome.desktop.background picture-uri file://%s" % imagePath
			command = command.split(" ")
			Popen(command)

		def linux_createCronJobs():
			#start cronjob
			cron_client = CronTab()
			iter =  cron_client.find_comment("Desktop Image Changer client")
			try:
				print "Client Cron Task Found"
				iter.next()
			except StopIteration:
				print 'Installing Client Cron Task'
				job = cron_client.new(scriptDirectory+ "/client.py dailyUpdate",
					comment="Desktop Image Changer client")
				job.every().dom()
				cron_client.write()

			cron_daemon = CronTab()
			iter =  cron_daemon.find_comment("Desktop Image Changer daemon")
			try:
				print "Daemon Cron Task Found"
				iter.next()
			except StopIteration:
				print 'Installing Daemon Cron Task'
				job = cron_daemon.new(scriptDirectory+ "/daemon.py &",
					comment="Desktop Image Changer daemon")
				job.every_reboot()
				cron_daemon.write()

		def linux_async_start():
			Popen(('python %s &' %  join_path(scriptDirectory, 'daemon.py')).split(' '))



		return (linux_getCurrentImageName, linux_changeDesktopImage, linux_createCronJobs, linux_async_start)

	else:
		print "os not supported"
		sys.exit(1)
