import sys,os,re,urllib,threading
from xml.dom.minidom import parseString as xml,Node

def listJar(basedir):
	import os
	jars=[(root,name) for root,dir,names in os.walk(basedir) for name in names if name.find('.jar')<>-1]
	return jars

def writeJarsMeta(basedir):
	jars=listJar(basedir)
	from zipfile import ZipFile as z
	uris = [os.path.join(dir,name) for dir,name in jars]
	meta_infos=map(lambda x:z(x).read('META-INF/MANIFEST.MF'),uris)
	file=open('meta-infos.txt','w')
	for uri,meta in zip(uris,meta_infos):
		file.write(uri)
		file.write(os.linesep)
		file.write(meta)
		file.write(os.linesep)

print_lock = threading.Lock()	

dependencyStr='''
<dependency>
	<groupId>%s</groupId>
	<artifactId>%s</artifactId>
	<version>%s</version>
</dependency>'''

class MvnRepoJar(threading.Thread):
	"""search one jar file for MvnRepository"""

	def __init__(self, file):
		threading.Thread.__init__(self)
		self.status=False
		self.file = file
		self.nameversion=file[0:-4]
		index=self.nameversion.rfind('-')
		self.name=self.nameversion[0:index]
		self.version=self.nameversion[index+1:]
		self.pom=None

	def readPage(self,url):
		for count in range(3):
			# with print_lock:
				# print '\t[Info]open url [%s]:%s' % (count,url)
			try:
				html= urllib.urlopen(url).read()
				return html
			except IOError:
				with print_lock:
					print "\t[Error]Oops!  networking failed...%s" % (count==2 and 'retry' or 'stop')

	def artifactHref(self):
		url='http://mvnrepository.com/search.html?query='+self.name
		html=self.readPage(url)
		tables=re.findall('<p class="result">.*?</p>',html,re.DOTALL)
		href=map(lambda table:re.findall('<a href="([^>]*?)" class="result-link">'+self.name+'</a>[^>]*?</p>',table,re.DOTALL),tables)
		href=[hasattr(h,'__iter__') and h[-1] or h   for h in href if h]
		return href

	def findHref(self):
		atf = self.artifactHref()
		if len(atf)==0 :
			return None
		if(len(atf)>1):
			with print_lock:
				# print  "\n"*300
				print '\t[Info][%s]possible href size:%d' % (threading.currentThread().file,len(atf))
				for x in range(1,len(atf)+1):
					print '\n\t\t[no:%d]:%s\t[no:%d]' % (x,atf[x-1],x)
				print "\tplease choose,input q for break this:"
				while True:
					try:
						cin= sys.stdin.readline()
						if(cin.strip()=='q'):
							print "ignored artifact %s " % threading.currentThread().file
							return None
						currentHref = atf[int(cin)-1]
						break
					except ValueError:
						print "value error,please reinput"
					except IndexError:
						print "out of index,please reinput"
		currentHref = atf[0]

		self.versionURL="http://mvnrepository.com"+currentHref
		self.versionHtml = self.readPage(self.versionURL)
		versionHref=re.search(r'<a class="versionbutton[^>]*?href="([^>]*?)">'+self.version+'</a>',self.versionHtml,re.DOTALL)
		if versionHref:
			self.href=self.versionURL+'/../'+versionHref.group(1)
			return self.href
		else:
			with print_lock:
				print "\t[Error]no special version found:%s" % self.file
			return None
	
	def genPomDep(self):
		with print_lock:
			print '[Info]==========start gen pom: %s' % self.file
		url = self.findHref()
		if not url:
			return None
		detailhtml = self.readPage(url)
		mvndep=re.search(r'<div id="tabs-1">(.*?)</div>',detailhtml,re.DOTALL)
		doc=xml(mvndep.group())
		trinity=[n for n in doc.getElementsByTagName('pre')[0].childNodes if n.nodeType==Node.TEXT_NODE and n.nodeValue.strip()]
		trinity=[n.nodeValue.replace('<','').replace('>','').replace('/','').strip() for n in trinity]
		self.trinity=tuple(filter(None,trinity))
		self.pom=dependencyStr % self.trinity
		return self.pom

	def run(self):
		self.genPomDep()


	def __str__(self):
		return self.file

def genDepen(trinity):
	dependencyStr='''
<dependency>
	<groupId>%s</groupId>
	<artifactId>%s</artifactId>
	<version>%s</version>
</dependency>'''
	return dependencyStr % trinity

if __name__ == '__main__':
	basedir='D:/workspace/java/wickit'
	jarsname=[name for dir,name in listJar(basedir)]
	l=[]
	for jar in jarsname:
		mvn = MvnRepoJar(jar)
		mvn.start()
		l.append(mvn)
	for t in l:
		t.join()
	sucess=''.join([mvn.pom for mvn in l if mvn.pom])
	file=open('result.txt','w')
	file.writelines(sucess)
	failed = '\n'.join([mvn.file for mvn in l if not mvn.pom])
	file.writelines(failed)