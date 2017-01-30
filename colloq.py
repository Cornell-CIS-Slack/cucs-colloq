#!/usr/bin/env python

import lxml.etree
import lxml.html
import urllib
import re
from datetime import datetime, timedelta
import dateutil.parser
from icalendar import Calendar, Event, vText, vUri
import paramiko
import pytz

FEED_URL = 'http://www.cs.washington.edu/events/colloquia-atom.xml'
PAGE_URL = 'http://www.cs.washington.edu/htbin-post/mvis/mvis/Colloquia'
COLLOQ_LENGTH = 60 # minutes
DEST_PATH = 'public_html/colloquia.ics'
BASE_HREF = 'http://www.cs.washington.edu'
SFTP_SERVER = 'recycle.cs.washington.edu'
TZINFO = pytz.timezone("America/Los_Angeles")

def parse_date(date):
    date = re.sub(r'-\d\d?:\d\d ', '', date) # remove time range
    out = dateutil.parser.parse(date.decode('utf8'))
    out = out.replace(tzinfo=TZINFO)
    return out

def make_event(title, date, stamp, location, link, speaker):
    event = Event()
    event.add('summary', title)
    event.add('dtstart', date)
    event.add('dtend', date + timedelta(minutes=COLLOQ_LENGTH))
    event.add('dtstamp', stamp)
    event['location'] = vText(location)
    event['uid'] = link
    event['description'] = vText(speaker)
    event['URL'] = vUri(link)
    return event

def event_id(url):
    return re.search(r'\?[iI][dD]=(\d+)', link).group(1)

cal = Calendar()
cal.add('prodid', '-//colloq.py//uwcse//')
cal.add('version', '2.0')
cal.add('X-WR-CALNAME', 'UW CSE Colloquia')
cal.add('X-WR-TIMEZONE', 'America/Los_Angeles')

event_ids = set()

tree = lxml.etree.parse(urllib.urlopen(FEED_URL))
root = tree.getroot()
for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
    title = entry.find('{http://www.w3.org/2005/Atom}title').text
    link = entry.find('{http://www.w3.org/2005/Atom}link').attrib['href']
    speaker = (entry.find('{http://www.w3.org/2005/Atom}author')
                    .find('{http://www.w3.org/2005/Atom}name').text)
    stamp = entry.find('{http://www.w3.org/2005/Atom}updated').text
    stamp = datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%SZ')
    stamp = stamp.replace(tzinfo=TZINFO)

    html = urllib.urlopen(link).read()
    date, location = re.search(r'</b><br>([^<]+)<br>([^<]*)<p>', html).groups()
    date = parse_date(date)

    event_ids.add(event_id(link))

    cal.add_component(make_event(title, date, stamp, location, link, speaker))

page = urllib.urlopen(PAGE_URL).read()
root = lxml.html.fragment_fromstring(page, create_parent='xxx')
dts = root.xpath('.//dt')
dds = root.xpath('.//dd')
for i in range(len(dts)):
    dt = dts[i]
    dd = dds[i]

    title = dt.xpath('./a')[0].xpath('string()')
    link = dt.xpath('./a/@href')[0]
    if '://' not in link:
        link = BASE_HREF + link
    speaker = dt.xpath('./b')[0].xpath('string()')
    dt_parts = [s.strip() for s in dt.xpath('./text()')]
    affiliation, date = [s for s in dt_parts if s]
    if affiliation:
        if affiliation.startswith('(') and affiliation.endswith(')'):
            affiliation = affiliation[1:-1]
        speaker += ', ' + affiliation
    date = parse_date(date)
    time, location = dd.xpath('./text()')[0].split(',', 1)
    hour, minute = time.strip().split(':')
    minute = minute.lower()
    if minute.endswith('am') or minute.endswith('pm'):
        if minute.endswith('pm'):
            hour = int(hour) + 12
            if hour == 24: # Noon special case.
                hour = 12
        minute = minute[:-2]
    date = date.replace(hour=int(hour), minute=int(minute))
    location = location.strip()

    if 'NO COLLOQUIUM SCHEDULED' in speaker:
        continue

    eid = event_id(link)
    if eid in event_ids:
        continue
    else:
        event_ids.add(eid)

    stamp = datetime.now()
    cal.add_component(make_event(title, date, stamp, location, link, speaker))

print cal.to_ical()

client = paramiko.SSHClient()
client.load_system_host_keys()
client.connect(SFTP_SERVER)
try:
    sftp = client.open_sftp()
    f = sftp.open(DEST_PATH, 'w')
    f.write(cal.to_ical())
    f.close()
    sftp.close()
finally:
    client.close()
