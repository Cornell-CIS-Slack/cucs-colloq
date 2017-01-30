#!/usr/bin/env python3

import bs4
import requests
import re
from datetime import timedelta
import dateutil.parser
from icalendar import Calendar, Event, vText, vUri
import pytz
import urllib.parse
import sys


PAGE_URL = 'https://www.cs.cornell.edu/events/colloquium'
COLLOQ_LENGTH = 60  # minutes
TZ = "America/New_York"
TZINFO = pytz.timezone(TZ)
CALNAME = 'Cornell CS Colloquia'
LOCATION = 'Gates G01'


def parse_date(date):
    out = dateutil.parser.parse(date)
    out = out.replace(tzinfo=TZINFO)
    return out


def make_event(title, date, location, link, speaker):
    event = Event()
    event.add('summary', title)
    event.add('dtstart', date)
    event.add('dtend', date + timedelta(minutes=COLLOQ_LENGTH))
    event['location'] = vText(location)
    event['uid'] = link
    event['description'] = vText(speaker or 'Colloquium')
    event['URL'] = vUri(link)
    return event


def scrape(url):
    """Get the event data from the public calendar URL.
    """
    req = requests.get(url)
    soup = bs4.BeautifulSoup(req.content, "html.parser")
    events_div = soup.find("div", class_="view-events")
    for listing in events_div.find_all("div", class_="event-listing"):
        # Extract the *easy* metadata.
        title = listing.find(class_="event-title").get_text().strip()
        date = listing.find(class_="date").get_text().strip()
        time = listing.find(class_="time").get_text().strip()
        link = listing.find(class_="event-title").find("a")['href']

        # Some harder metadata is hidden in the strings.
        text = listing.get_text()
        match = re.search(r'Speaker:\s+(.*)', text)
        speaker = match.group(1).strip() if match else None
        match = re.search(r'Host:\s+(.*)', text)
        host = match.group(1).strip() if match else None

        yield {
            'title': title,
            'date': date,
            'time': time,
            'speaker': speaker,
            'host': host,
            'link': link,
        }


def colloq():
    cal = Calendar()
    cal.add('prodid', '-//colloq.py//cucs//')
    cal.add('version', '2.0')
    cal.add('X-WR-CALNAME', CALNAME)
    cal.add('X-WR-TIMEZONE', TZ)

    for event in scrape(PAGE_URL):
        date = parse_date(event['date'])

        cal.add_component(make_event(
            event['title'],
            date,
            LOCATION,
            urllib.parse.urljoin(PAGE_URL, event['link']),
            event['speaker'],
        ))

    sys.stdout.buffer.write(cal.to_ical())


if __name__ == '__main__':
    colloq()
