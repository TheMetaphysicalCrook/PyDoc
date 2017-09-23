import requests
import re
import json
import ast
import os
import ui
import threading
import tarfile
import math
import time
import plistlib
import console
import shutil
import sqlite3
from Managers import DBManager, TypeManager
from Utilities import LogThread

class Cheatsheet (object):
	def __init__(self):
		self.__version = ''
		self.__globalversion = ''
		self.__name = ''
		self.__aliases = []
		self.__icon = None
		self.__id = ''
		self.__path = None
		self.__status = ''
		self.__stats = ''
		self.__onlineid = ''
		
	@property
	def onlineid(self):
		return self.__onlineid
	
	@onlineid.setter
	def onlineid(self, id):
		self.__onlineid = id	
		
	@property
	def version(self):
		return self.__version
	
	@version.setter
	def version(self, version):
		self.__version = version
	
	@property
	def globalversion(self):
		return self.__globalversion
	
	@globalversion.setter
	def globalversion(self, globalversion):
		self.__globalversion = globalversion
	
	@property
	def name(self):
		return self.__name
	
	@name.setter
	def name(self, name):
		self.__name = name
		
	@property
	def aliases(self):
		return self.__aliases
	
	@aliases.setter
	def aliases(self, aliases):
		self.__aliases = aliases
		
	@property
	def image(self):
		return self.__icon
	
	@image.setter
	def image(self, icon):
		self.__icon = icon
	
	@property
	def id(self):
		return self.__id
	
	@id.setter
	def id(self, id):
		self.__id = id	
	
	@property
	def path(self):
		return self.__path
	
	@path.setter
	def path(self, path):
		self.__path = path
		
	@property
	def status(self):
		return self.__status
	
	@status.setter
	def status(self, status):
		self.__status = status
		
	@property
	def stats(self):
		return self.__stats
	
	@stats.setter
	def stats(self, stats):
		self.__stats = stats
		
class CheatsheetManager (object):
	def __init__(self, serverManager, iconPath, typeIconPath):
		self.typeManager = TypeManager.TypeManager(typeIconPath)
		self.serverManager = serverManager
		self.iconPath = iconPath
		self.typeIconPath = typeIconPath
		self.localServer = None
		self.jsonServerLocation = 'zzz/cheatsheets/cheat.json'
		self.downloadServerLocation = 'zzz/cheatsheets/%@.tgz'
		self.plistPath = 'Contents/Info.plist'
		self.indexPath = 'Contents/Resources/docSet.dsidx'
		self.cheatsheetFolder = 'Docsets/Cheatsheets'
		self.headers = {'User-Agent': 'PyDoc-Pythonista'}
		self.cheatsheets = None
		self.downloading = []
		self.workThreads = []
		self.downloadThreads = []
		self.uiUpdateThreads = []
		self.__createCheatsheetFolder()
	
	def getAvailableCheatsheets(self):
		cheatsheets = self.__getOnlineCheatsheets()
		for d in self.__getDownloadedCheatsheets():
			for c in cheatsheets:
				if c.name == d.name:
					c.status = 'installed'
					c.path = d.path
					c.id = d.id
		for d in self.__getDownloadingCheatsheets():
			for c in cheatsheets:
				if c.name == d.name:
					c.status = d.status
					try:
						c.stats = d.stats
					except KeyError:
						c.stats = 'downloading'
		return cheatsheets
	
	def __getOnlineCheatsheets(self):
		if self.cheatsheets == None:
			self.cheatsheets = self.__getCheatsheets()
		return self.cheatsheets
	
	def __getDownloadedCheatsheets(self):
		ds = []
		dbManager = DBManager.DBManager()
		t = dbManager.InstalledDocsetsByType('cheatsheet')
		ds = []
		for d in t:
			aa = Cheatsheet()
			aa.name = d[1]
			aa.id = d[0]
			aa.path = os.path.join(os.path.abspath('.'),d[2])
			aa.image = self.__getIconWithName(d[4])
			ds.append(aa)
		return ds
	
	def __getDownloadingCheatsheets(self):
		return self.downloading
		
	def getDownloadedCheatsheets(self):
		return self.__getDownloadedCheatsheets()
		
	def __getCheatsheets(self):
		server = self.serverManager.getDownloadServer(self.localServer)
		url = server.url
		if not url[-1] == '/':
			url = url + '/'
		url = url + self.jsonServerLocation
		data = requests.get(url).text
		data = ast.literal_eval(data)
		
		cheatsheets = []
		icon = self.__getIconWithName('cheatsheet')
		for k,d in data['cheatsheets'].items():
			c = Cheatsheet()
			c.name = d['name']
			c.aliases = d['aliases']
			c.globalversion = data['global_version']
			c.version = d['version']
			c.image = icon
			c.onlineid = k
			c.status = 'online'
			cheatsheets.append(c)
		return sorted(cheatsheets, key=lambda x: x.name.lower())
	
	def __getIconWithName(self, name):
		imgPath = os.path.join(os.path.abspath('.'), self.iconPath, name+'.png')
		if not os.path.exists(imgPath):
			imgPath = os.path.join(os.path.abspath('.'), self.iconPath, 'Other.png')
		return ui.Image.named(imgPath)
	
	def __createCheatsheetFolder(self):
		if not os.path.exists(self.cheatsheetFolder):
			os.mkdir(self.cheatsheetFolder)
		
	def downloadCheatsheet(self, cheatsheet, action, refresh_main_view):
		if not cheatsheet in self.downloading:
			cheatsheet.status = 'downloading'
			self.downloading.append(cheatsheet)
			action()
			workThread = LogThread.LogThread(target=self.__determineUrlAndDownload, args=(cheatsheet,action,refresh_main_view,))
			self.workThreads.append(workThread)
			workThread.start()
	
	def __determineUrlAndDownload(self, cheatsheet, action, refresh_main_view):
		cheatsheet.stats = 'getting download link'
		action()
		downloadLink = self.__getDownloadLink(cheatsheet.onlineid)
		downloadThread = LogThread.LogThread(target=self.downloadFile, args=(downloadLink,cheatsheet,refresh_main_view,))
		self.downloadThreads.append(downloadThread)
		downloadThread.start()
		updateThread = LogThread.LogThread(target=self.updateUi, args=(action,downloadThread,))
		self.uiUpdateThreads.append(updateThread)
		updateThread.start()

	def updateUi(self, action, t):
		while t.is_alive():
			action()
			time.sleep(0.5)
		action()
	
	def __getDownloadLink(self, id):
		server = self.serverManager.getDownloadServer(self.localServer)
		url = server.url
		if not url[-1] == '/':
			url = url + '/'
		url = url + self.downloadServerLocation
		url = url.replace('%@', id)
		return url
	
	def downloadFile(self, url, cheatsheet, refresh_main_view):
		local_filename = self.__downloadFile(url, cheatsheet)
		#self.__downloadFile(url+'.tarix', cheatsheet)
		cheatsheet.status = 'waiting for install'
		self.installCheatsheet(local_filename, cheatsheet, refresh_main_view)
	
	def __downloadFile(self, url, cheatsheet):
		local_filename = self.cheatsheetFolder+'/'+url.split('/')[-1]
		r = requests.get(url, headers = self.headers, stream=True)
		ret = None
		if r.status_code == 200:
			ret = local_filename
			total_length = r.headers.get('content-length')
			dl = 0
			last = 0
			if os.path.exists(local_filename):
				os.remove(local_filename)
			with open(local_filename, 'wb') as f:
				for chunk in r.iter_content(chunk_size=1024): 
					if chunk: # filter out keep-alive new chunks
						dl += len(chunk)
						f.write(chunk)
						if not total_length == None:
							done = 100 * dl / int(total_length)
							cheatsheet.stats = str(round(done,2)) + '% ' + str(self.convertSize(dl)) + ' / '+ str(self.convertSize(float(total_length)))
						else:
							 cheatsheet.stats = str(self.convertSize(dl))
		
		r.close()	
		return ret		
		
	def installCheatsheet(self, filename, cheatsheet, refresh_main_view):
		extract_location = self.cheatsheetFolder
		cheatsheet.status = 'Preparing to install: This might take a while.'
		tar = tarfile.open(filename, 'r:gz')
		n = [name for name in tar.getnames() if '/' not in name][0]
		m = os.path.join(self.cheatsheetFolder, n)
		tar.extractall(path=extract_location, members = self.track_progress(tar, cheatsheet, len(tar.getmembers())))
		tar.close()
		os.remove(filename)
		dbManager = DBManager.DBManager()
		dbManager.DocsetInstalled(cheatsheet.name, m, 'cheatsheet', 'cheatsheet', cheatsheet.version)
		if cheatsheet in self.downloading:
			self.downloading.remove(cheatsheet)
		self.indexCheatsheet(cheatsheet, refresh_main_view, m)
	
	def track_progress(self, members, cheatsheet, totalFiles):
		i = 0
		for member in members:
			i = i + 1
			done = 100 * i / totalFiles
			cheatsheet.status = 'installing: ' + str(round(done,2)) + '% ' + str(i) + ' / '+ str(totalFiles) 
			yield member
	
	def indexCheatsheet(self, cheatsheet, refresh_main_view, path):
		cheatsheet.status = 'indexing'
		indexPath = os.path.join(path, self.indexPath)
		conn = sqlite3.connect(indexPath)
		sql = 'SELECT count(*) FROM sqlite_master WHERE type = \'table\' AND name = \'searchIndex\''
		c = conn.execute(sql)
		data = c.fetchone()
		if int(data[0]) == 0:
			sql = 'CREATE TABLE searchIndex(rowid INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT)'
			c = conn.execute(sql)
			conn.commit()
			sql = 'SELECT f.ZPATH, m.ZANCHOR, t.ZTOKENNAME, ty.ZTYPENAME, t.rowid FROM ZTOKEN t, ZTOKENTYPE ty, ZFILEPATH f, ZTOKENMETAINFORMATION m WHERE ty.Z_PK = t.ZTOKENTYPE AND f.Z_PK = m.ZFILE AND m.ZTOKEN = t.Z_PK ORDER BY t.ZTOKENNAME'
			c = conn.execute(sql)
			data = c.fetchall()
			for t in data:
				conn.execute("insert into searchIndex values (?, ?, ?, ?)", (t[4], t[2], self.typeManager.getTypeForName(t[3]).name, t[0] ))
				conn.commit()
		else:
			sql = 'SELECT rowid, type FROM searchIndex'
			c = conn.execute(sql)
			data = c.fetchall()
			for t in data:
				newType = self.typeManager.getTypeForName(t[1])
				if not newType == None and not newType.name == t[1]:
					conn.execute("UPDATE searchIndex SET type=(?) WHERE rowid = (?)", (newType.name, t[0] ))
				conn.commit()
		conn.close()
		self.postProcess(cheatsheet, refresh_main_view)
		
	def postProcess(self, cheatsheet, refresh_main_view):
		cheatsheet.status = 'installed'
		refresh_main_view()

	def convertSize(self, size):
		if (size == 0):
			return '0B'
		size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
		i = int(math.floor(math.log(size,1024)))
		p = math.pow(1024,i)
		s = round(size/p,2)
		return '%s %s' % (s,size_name[i])
	
	def deleteCheatsheet(self, cheatsheet, post_action):
		but = console.alert('Are you sure?', 'Would you like to delete the cheatsheet, ' +  cheatsheet.name, 'Ok')
		if but == 1:
			dbmanager = DBManager.DBManager()
			dbmanager.DocsetRemoved(cheatsheet.id)
			shutil.rmtree(cheatsheet.path)
			cheatsheet.status = 'online'
			post_action()
			cheatsheet.path = None
	
	def getTypesForCheatsheet(self, cheatsheet):
		types = []
		path = cheatsheet.path
		indexPath = os.path.join(path, self.indexPath)
		conn = sqlite3.connect(indexPath)
		sql = 'SELECT type FROM searchIndex GROUP BY type ORDER BY type COLLATE NOCASE'
		c = conn.execute(sql)
		data = c.fetchall()
		conn.close()
		for t in data:
			types.append(self.typeManager.getTypeForName(t[0]))
		return types
	
	def getIndexesbyTypeForCheatsheet(self, cheatsheet, type):
		indexes = []
		path = cheatsheet.path
		indexPath = os.path.join(path, self.indexPath)
		conn = sqlite3.connect(indexPath)
		sql = 'SELECT type, name, path FROM searchIndex WHERE type = (?) ORDER BY name COLLATE NOCASE'
		c = conn.execute(sql, (type.name,))
		data = c.fetchall()
		conn.close()
		for t in data:
			indexes.append({'type':self.typeManager.getTypeForName(t[0]), 'name':t[1],'path':t[2]})
		return indexes
	
	def getIndexesbyTypeAndNameForDocset(self, cheatsheet, typeName, name):
		indexes = []
		path = cheatsheet.path
		indexPath = os.path.join(path, self.indexPath)
		conn = sqlite3.connect(indexPath)
		sql = 'SELECT type, name, path FROM searchIndex WHERE type = (?) AND name LIKE (?) ORDER BY name COLLATE NOCASE'
		c = conn.execute(sql, (typeName, name,))
		data = c.fetchall()
		conn.close()
		for t in data:
			indexes.append({'type':self.typeManager.getTypeForName(t[0]), 'name':t[1],'path':t[2]})
		return indexes
		
	def getIndexesByNameForDocset(self, cheatsheet, name):
		indexes = []
		path = cheatsheet.path
		indexPath = os.path.join(path, self.indexPath)
		conn = sqlite3.connect(indexPath)
		sql = 'SELECT type, name, path FROM searchIndex WHERE name LIKE (?) ORDER BY name COLLATE NOCASE'
		c = conn.execute(sql, (name,))
		data = c.fetchall()
		conn.close()
		for t in data:
			indexes.append({'type':self.typeManager.getTypeForName(t[0]), 'name':t[1],'path':t[2]})
		return indexes
	
	def getIndexesForCheatsheet(self, cheatsheet):
		indexes = []
		path = cheatsheet.path
		indexPath = os.path.join(path, self.indexPath)
		conn = sqlite3.connect(indexPath)
		sql = 'SELECT type, name, path FROM searchIndex ORDER BY name COLLATE NOCASE'
		c = conn.execute(sql)
		data = c.fetchall()
		conn.close()
		for i in data:
			indexes.append({'type':self.typeManager.getTypeForName(t[0]), 'name':t[1],'path':t[2]})
		return types
		
	def getIndexesbyNameForAllCheatsheet(self, name):
		if name == None or name == '':
			return []
		else:
			name = '%'+name+'%'
			docsets = self.getDownloadedCheatsheets()
			indexes = []
			for d in docsets:
				ind = []
				path = d.path
				indexPath = os.path.join(path, self.indexPath)
				conn = sqlite3.connect(indexPath)
				sql = 'SELECT type, name, path FROM searchIndex WHERE name LIKE (?) OR name LIKE (?) ORDER BY name COLLATE NOCASE'
				c = conn.execute(sql, (name, name.replace(' ','%'),))
				data = c.fetchall()
				conn.close()
				dTypes = {}
				for t in data:
					url = 'file://' + os.path.join(path, 'Contents/Resources/Documents', t[2])
					url = url.replace(' ', '%20')
					type = None
					if t[0] in dTypes.keys():
						type= dTypes[t[0]]
					else:
						type = self.typeManager.getTypeForName(t[0])
						dTypes[t[0]] = type
					ind.append({'name':t[1], 'path':url, 'icon':d.image,'docsetname':d.name,'type':type})
				indexes.extend(ind)
			return indexes
			
	def getIndexesbyNameForDocset(self, docset, name):
		if name == None or name == '':
			return []
		else:
			name = '%'+name+'%'
			ind = []
			path = docset.path
			indexPath = os.path.join(path, self.indexPath)
			conn = sqlite3.connect(indexPath)
			sql = 'SELECT type, name, path FROM searchIndex WHERE name LIKE (?) OR name LIKE (?) ORDER BY name COLLATE NOCASE'
			c = conn.execute(sql, (name, name.replace(' ','%'),))
			data = c.fetchall()
			conn.close()
			dTypes = {}
			for t in data:
				url = 'file://' + os.path.join(path, 'Contents/Resources/Documents', t[2])
				url = url.replace(' ', '%20')
				type = None
				if t[0] in dTypes.keys():
					type= dTypes[t[0]]
				else:
					type = self.typeManager.getTypeForName(t[0])
					dTypes[t[0]] = type
				ind.append({'name':t[1], 'path':url, 'icon':docset.image,'docsetname':docset.name,'type':type})
			return ind
		
if __name__ == '__main__':
	import ServerManager
	c = CheatsheetManager(ServerManager.ServerManager(), '../Images/icons')
		
