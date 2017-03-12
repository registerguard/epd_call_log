#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import environ
import sys

sys.path.append('/rgcalendar/oper')
sys.path.append('/rgcalendar/oper/projects_root')
environ['DJANGO_SETTINGS_MODULE'] = 'projects_root.settings'
from projects_root.epd.models import Incident
from django.db.utils import DatabaseError
from geopy import geocoders
from geopy.geocoders.googlev3 import GQueryError, GTooManyQueriesError

def main(backfill_date = None, priority_group = None, my_eight_digit_date = None):
    '''
    Parse police call log Web page prodcued by from SunGard Records Management 
    System/Computer Aided Dispatch system (RMS/CAD) used by Eugene and 
    Springfield, Ore., and insert into a Django application (not included).
    '''
    
    import datetime
    import re
    import time
    import urllib
    import urllib2
    
    from bs4 import BeautifulSoup
    from dateutil.parser import parse
    
    if len(sys.argv) > 1:
        my_eight_digit_date = sys.argv[1]
        date_string = datetime.date(int(sys.argv[1][:4]), int(sys.argv[1][4:6]), int(sys.argv[1][6:])).strftime("%m/%d/%Y")
    elif backfill_date:
         date_string = backfill_date
    else:
        today = datetime.date.today()
        my_eight_digit_date = today.strftime("%m/%d/%Y")
        date_string = today.strftime("%m/%d/%Y")
    
    url = 'http://coeapps.eugene-or.gov/EPDDispatchLog/Search'
    if priority_group:
        values = {
            'DateFrom': date_string, 
            'DateThrough': date_string, 
            'IncidentType': '', 
            'Disposition': '', 
            'Priority': priority_group, 
            'EventNumberFilterOption': 'IsExactly', 
            'EventNumber': '', 
            'StreetNumberFilterOption': 'IsExactly', 
            'StreetNumber': '', 
            'StreetNameFilterOption': 'IsExactly', 
            'StreetName': '', 
            'CaseNumberFilterOption': 'IsExactly', 
            'CaseNumber': '',
        }
    else:
        values = {
            'DateFrom': date_string, 
            'DateThrough': date_string, 
            'IncidentType': '', 
            'Disposition': '', 
            'Priority': '', 
            'EventNumberFilterOption': 'IsExactly', 
            'EventNumber': '', 
            'StreetNumberFilterOption': 'IsExactly', 
            'StreetNumber': '', 
            'StreetNameFilterOption': 'IsExactly', 
            'StreetName': '', 
            'CaseNumberFilterOption': 'IsExactly', 
            'CaseNumber': '',
        }
    data = urllib.urlencode(values)
    req = urllib2.Request(url, data)
    response = urllib2.urlopen(req)
    the_page = response.read()
    
    soup = BeautifulSoup(the_page)
    
    body = soup.findAll('tbody')[0]
    rows = body.findAll('tr')
    call_count = len(rows)
    
    if call_count != 250:
        for tr in rows:
            cols = tr.findAll('td')
# 
# Sept. 16, 2014; Eugene added a "Map" column to the page we're scraping.
# Had to increment list item integers
# 
#             call_time, dispatch_time, incident_desc, officers, disposition, event_number, location, priority, case = \
#             cols[0].string, cols[1].string, cols[2].string, cols[3].string, cols[4].string, cols[5].string, cols[6].string, cols[7].string, cols[8].string
            call_time, dispatch_time, incident_desc, officers, disposition, event_number, location, priority, case = \
            cols[1].string, cols[2].string, cols[3].string, cols[4].string, cols[5].string, cols[6].string, cols[7].string, cols[8].string, cols[9].string
            
            # use dateutils to convert datetime strings to datetime objects
            if call_time:
                call_time = parse(call_time)
            if dispatch_time:
                dispatch_time = parse(dispatch_time)
            
#             location = location.replace('/', ' & ')
            location = location.replace('HWY 99N', 'OR-99')
            location = location.replace('-BLK', '')
            
            # space out, replace '/' on locations, i.e.:
            # IN -> 'W BROADWAY/OLIVE ST, EUG'
            # OUT -> 'W BROADWAY & OLIVE ST, EUG'
            # while leaving 1/2, as in '1966 1/2 ORCHARD ST' alone ... 
            location = re.sub('([^1])/([^2])', '\\1 & \\2', location)
            location = re.sub('(COT) $', '\\1TTAGE GROVE ', location)
            location = re.sub('(CRE) $', '\\1SWELL ', location)
            location = re.sub('(EUG) $', '\\1ENE ', location)
            location = re.sub('(FAL) $', '\\1L CREEK ', location)
            location = re.sub('(SPR) $', '\\1INGFIELD ', location)
            location = re.sub('(HAR) $', '\\1RISBURG ', location)
            location = re.sub('(VEN) $', '\\1ETA ', location)
            location = re.sub('(FLO) $', '\\1RENCE ', location)
            
            # new system (as of Nov. 22, 2013) has a priority 
            # of 'P', but it's stored in an integer field, so this doesn't fly. 
            # For consistency, a hack to covert it to 6, which is what it was 
            # in previous EPD system.
            priority = unicode(priority)
            if priority.strip() == 'P':
                priority = 6
            elif priority:
                try:
                    priority = int(unicode(priority))
                except ValueError:
                    priority = None
            
            # strip out alpha prefixes on officers, introduced in Nov. 22, 2013 
            # system changeover.
            if officers:
                officers = officers.rstrip()
                officers = re.sub('EPD|V|CAH|-9999     ', u'', officers)
                officers = officers.split('     ')
                # remove duplicate badge numbers
                officers = list(set(officers))
                officers = ', '.join(officers)
            else:
               # officers can't be None
               officers = ''
            
            # 
            # From http://www.crummy.com/software/BeautifulSoup/bs4/doc/
            # 
            # " ... If you want to use a NavigableString outside of Beautiful 
            # Soup, you should call unicode() on it to turn it into a normal 
            # Python Unicode string. If you don’t, your string will carry 
            # around a reference to the entire Beautiful Soup parse tree, even 
            # when you’re done using Beautiful Soup. This is a big waste of 
            # memory. ... "
            incident_desc = unicode(incident_desc)
            disposition = unicode(disposition)
            event_number = unicode(event_number)
            case = unicode(case)
            
            #
            # Changed get_or_create lookup to 'Event number' from 'ID', as EPD started re-using 'ID's Sept. 11, 2009.
            #
            try:
                geocoded_by = None
                place = None
                lat = None
                lng = None
                
                # Monkey-patch the city on. Springfield seems fond of not 
                # including the city name.
                if not location.count(','):
                    location = location + ', EUGENE'
                
                Incident_instance, created = Incident.objects.get_or_create(
                    event_number = event_number, 
                    incident_description = unicode(incident_desc), 
                    defaults = {
                    'police_response': dispatch_time,
#                     'incident_description': unicode(incident_desc),
                    'ofc': officers,
                    'received': call_time,
                    'disp': unicode(disposition),
                    'location': location,
                    'pd_id': unicode(event_number),
                    'priority': priority,
                    'case_no': unicode(case),
                    'comment': '',
                    }
                )
                
                # To geocode economically, only do so if there's been an 
                # Incident created.
                if created and location:
                    '''
                    Sept. 11, 2013: Switching from v2 to v3 Google geocoder.
                    https://github.com/geopy/geopy/blob/master/docs/google_v3_upgrade.md
                
                    # g = geocoders.Google('ABQIAAAAipqnSW_ox-DaZp8gNuT_qRQeQVg07lpBkUqRt1DZ_A2Xwczm_BSE7XC4NVMUh0B3nE-UHYsFJrvxUA')
                    '''
                    g = geocoders.GoogleV3()
                    try:
                        place, (lat, lng) = g.geocode(location + ', OR')
                        geocoded_by = 'Google'
                    except (ValueError, GQueryError):
                        pass # no address found
                    except GTooManyQueriesError:
                        g = geocoders.Bing('AkT3k27Ym8h7YxSjiAG-N58w4OPm3nR-4miH9y576YvN9QEw5kJTqOcIAy3DBqX6')
                        place, (lat, lng) = g.geocode(location + ', OR')
                        geocoded_by = 'Bing!'
                    if lat:
                        Incident_instance.lat = str(lat)
                    if lng:
                        Incident_instance.lng = str(lng)
                    
                    Incident_instance.save()
                    
                    # If my_eight_digit_date exists, then we're probably 
                    # running the script manually, so it's likely to be a 
                    # bulk data back-fill situation and Google v3 geocoder 
                    # doesn't care for lots of requests in a burst; it shuts 
                    # down; so, we insert this time.sleep() bit ...
                    if my_eight_digit_date:
                        print 'Saved lat, long for %s; received %s. Geocoded by %s.' % (place, Incident_instance.received.strftime('%I:%M %p, %A, %B %d, %Y'), geocoded_by) 
#                             time.sleep(0.25) 
            
            except (DatabaseError, ValueError), err:
                print 'DatabaseError or ValueError >>>', call_time, location, officers
                print 'Error:', err
        else:
#                 print 'Ignored', incident_dict['Event Number'], 'No \'Incident Description\''
            pass
            
    else:
        # TO DO: What to do if it's a truncated, 250-item count ... 
        print "Truncated results"
        priority_list=('P', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9')
        for priority_code in priority_list:
            print '    Looking up priority code %s' % priority_code
            main(priority_group=priority_code)
    
    print 'Call count:', call_count

if __name__ == "__main__" : main()
