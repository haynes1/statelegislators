import sys
import os
sys.path.insert(0, '../lib')

import urllib2
from bs4 import BeautifulSoup
import twitterparse as twp
import json
import re
from statebioguides import StateBioguides
from dbconnection import DBConnection

sbid = StateBioguides()
db = DBConnection()

def sanitizeName(i):
	i = i.replace("Representative ", "")
	i = i.replace("Senator ", "")
	raw_party = i[-3:]
	name = i[:-4]
	party = raw_party.replace("(","").replace(")","")
	return name,party

def sanitizeDistrictName(i):
	a = "".join(i.split("\t"))
	a = "".join(a.split("\r"))
	return "".join(a.split("\n"))

def sanitizeLeadership(l):
	l = "".join(l.split("\r"))
	l = "".join(l.split("$$$"))
	l = "".join(l.split("\n"))
	l = "".join(l.split(" "))
	l = "".join(l.split("\t"))
	return l

def sanitizeCountyList(l):
	l = "".join(l.split(" "))
	l = "".join(l.split("\t"))
	l = "".join(l.split("\r"))
	l = "".join(l.split("\n"))
	l = ", ".join(l.split("$$$"))
	return l[:-2]

def sanitizePhoneList(l):
	for br in l.find_all("br"):
		br.replace_with("$$$")
	raw = l.text.split("$$$")[0]
	raw = re.sub("[^0-9]", "", raw)
	phone = raw[0:3] + "-" + raw[3:6] + "-" + raw[6:10]
	if len(raw) > 10:
		phone = phone + " ext: " + raw[10:]
	return phone

def sanitizeAddress(a):
	lines = []
	for br in a.find("br"):
		try:
			lines.append(br.text)
			br.replace_with("")
		except:
			if len(br) > 8:
				lines.append(br)
			br.replace_with("")
	return a.text + ", " + " ".join(lines)

def processSingleKYLegislator(url):
	req = urllib2.urlopen(url).read()
	soup = BeautifulSoup(req, "html.parser")

	office = {}
	office_misc = {}
	official = {}
	official_misc = {}

	bioheader = soup.find("div", {"id":"bioHeader"})
	official["name"],official["party"] = sanitizeName(bioheader.find("span", {"id":"name"}).text)
	office["name"] = sanitizeDistrictName(bioheader.find("span",{"id":"districtHeader"}).text)
	office_misc["County List"] = sanitizeCountyList(bioheader.find("span", {"id":"countyList"}).text)
	official["leadershiprole"] = sanitizeLeadership(bioheader.find("div", {"id":"bioLeaderTitle"}).text)
	member_information = soup.find("div", {"class":"memberInformation"})
	official_misc["home_city"] = member_information.find("div", {"id":"HomeCity"}).find("span",{"class":"bioText"}).text
	office["address"] = sanitizeAddress(member_information.find("div",{"id":"MailingAddress"}).find("span",{"class":"bioText"}))
	office["phone"] = sanitizePhoneList(member_information.find("div",{"id":"PhoneNumbers"}).find("span",{"class":"bioText"}))
	official["twitter"] = member_information.find("div",{"id":"TwitterHandle"}).find("span",{"class":"bioText"}).text[1:]
	official_misc["service"] = member_information.find("div",{"id":"Service"}).find("span",{"class":"bioText"}).text
	office["source"] = url
	official["source"] = url
	distnum = int(office["name"].split(" ")[len(office["name"].split(" ")) - 1])
	dcbase = "country:us/state:ky/"
	dcnum = int(office["name"][len(office["name"]) - 1])
	if "Senate" in office["name"]:
		office["title"] = "Kentucky State Senator"
		office["shorttitle"] = "KY Sen."
		office["districtcode"] = dcbase + "sldu:" + str(dcnum)
	else:
		office["title"] = "Kentucky State Representative"
		office["shorttitle"] = "KY Rep."
		office["districtcode"] = dcbase + "sldl:" + str(dcnum)

	ne = official["name"].split(" ")
	ne = [x for x in ne if x]
	firstname = ne[0]
	lastname = ne[len(ne) - 1]

	#create bioguide
	official["bioguide"] = sbid.getBioguide(lastname,firstname,office["districtcode"])[0][0]
	office["bioguide"] = official["bioguide"]

	try:
		ppic = twp.getProfilePic(official["twitter"])
	except:
		ppic = None

	db.insertDict(office,"offices")
	db.insertDict(official,"officials")

	#print "\n"



def getKYLegislators():

	chamber_urls = ["http://www.lrc.ky.gov/whoswho/sendist.htm", "http://www.lrc.ky.gov/whoswho/hsedist.htm"]

	for chamber_url in chamber_urls:
		req = urllib2.urlopen(chamber_url).read()
		soup = BeautifulSoup(req, "html.parser")
		table = soup.find("table", {"id":"innerTable"})
		for tr in table.findAll("tr"):
			if len(tr.findAll("td")) < 2:
				continue
			a = tr.findAll("td")[1].find("a")
			if a == None:
				print tr
				print "Error: " + str(tr.findAll("td")[1].text) + " " + str(tr.findAll("td")[0].text)
				continue
			print a["href"]
			processSingleKYLegislator(a["href"])


getKYLegislators()

#processSingleKYLegislator("http://www.lrc.ky.gov/legislator/H080.htm")