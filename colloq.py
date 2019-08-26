#!/usr/bin/env python3

import bs4
import requests
import re
from datetime import timedelta, datetime
import dateutil.parser
from icalendar import Calendar, Event, vText, vUri
import pytz
import urllib.parse
import sys
import csv


TOC_URL = 'http://www.cs.cornell.edu/events'
LINK_NAME = 'CS Colloquium'
COLLOQ_LENGTH = 70  # minutes
TZ = "America/New_York"
TZINFO = pytz.timezone(TZ)
CALNAME = 'Cornell CS Colloquia'
LOCATION = 'Gates G01'
PREFIX_RE = r'CS Colloquium: '
SKIP_PREFIX_RES = (r'No Colloquium', r'No CS Colloquium')
SPEAKER_URL_RE = r'<strong>Speaker:<\/strong>\s<span><a href="(.*)">.*<\/a><\/span>'
SPEAKER_HYPERLINK = "=HYPERLINK(\"{1}\",\"{0}\")"


def parse_date(date):
    """Parse a date from (any) string."""

    out = dateutil.parser.parse(date)
    out = out.replace(tzinfo=TZINFO)
    return out


def make_event(title, date, location, link, speaker):
    """Make an iCal `Event` object from the colloquium details."""

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
    """Get the event data from the public calendar URL."""

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
        match = re.search(SPEAKER_URL_RE, str(listing))
        speaker_url = match.group(1).strip() if match else None
        match = re.search(r'Host:\s+(.*)', text)
        host = match.group(1).strip() if match else None

        yield {
            'title': title,
            'date': date,
            'time': time,
            'speaker': speaker,
            'speaker_url': speaker_url,
            'host': host,
            'link': link,
        }


def find_colloq_url(toc_url, link_name):
    """Scrape a table-of-contents page to find the current CS colloquium
    link.
    """
    req = requests.get(toc_url)
    soup = bs4.BeautifulSoup(req.content, "html.parser")
    for menu in soup.find_all("ul", class_="menu"):
        for link in menu.find_all("a"):
            if link.get_text() == link_name:
                path = link['href']
                return urllib.parse.urljoin(toc_url, path)
    assert False, "could not find schedule link"


def colloq():
    """Produce an iCal file on stdout and a CSV output file for the colloquia."""
    page_url = find_colloq_url(TOC_URL, LINK_NAME)

    cal = Calendar()
    cal.add('prodid', '-//colloq.py//cucs//')
    cal.add('version', '2.0')
    cal.add('X-WR-CALNAME', CALNAME)
    cal.add('X-WR-TIMEZONE', TZ)

    with open("colloq.csv", 'w') as ofile:
        header = [
                "Colloquium Date",
                "Czar 1",
                "Czar 2",
                "Name",
                "Affiliation",
                "Title/Abstract",
                "Host",
            ]
        writer = csv.DictWriter(ofile, fieldnames=header)

        for event in scrape(page_url):
            date = parse_date(event['date'] + ' ' + event['time'])
            title = re.sub(PREFIX_RE, '', event['title'])

            # Check whether this entry says there's no colloquium.
            skip = False
            for skip_prefix_re in SKIP_PREFIX_RES:
                if re.match(skip_prefix_re, title):
                    skip = True
                    break
            if skip:
                continue

            cal.add_component(make_event(
                title,
                date,
                LOCATION,
                urllib.parse.urljoin(page_url, event['link']),
                event['speaker'],
            ))

            # Hyperlink for CSV for Google Sheets
            speaker = SPEAKER_HYPERLINK.format(event['speaker'], event['speaker_url'])

            # Simplify TBD titles
            title = "TBD" if ("Title TBD" in event['title']) else event['title']

            row = {
                    "Colloquium Date" : date.strftime("%m/%d/%Y"),
                    "Czar 1" : "",
                    "Czar 2" : "",
                    "Name" : speaker,
                    "Affiliation" : "",
                    "Title/Abstract" : title,
                    "Host" : event['host'],
                }

            writer.writerow(row)

    sys.stdout.buffer.write(cal.to_ical())


if __name__ == '__main__':
    colloq()
