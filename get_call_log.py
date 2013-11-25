#!/usr/bin/env python

def main(backfill_date = ''):
    '''
    Parse police call log Web page prodcued by from SunGard Records Management 
    System/Computer Aided Dispatch system (RMS/CAD) used by Eugene and 
    Springfield, Ore., and insert into a Django application (not included).
    '''
    
    import datetime
    import sys
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
            call_time, dispatch_time, incident_desc, officers, disposition, event_number, location, priority, case = \
            cols[0].string, cols[1].string, cols[2].string, cols[3].string, cols[4].string, cols[5].string, cols[6].string, cols[7].string, cols[8].string
            
            # use dateutils to convert datetime strings to datetime objects
            call_time = parse(call_time)
            dispatch_time = parse(dispatch_time)
            
            # space out, replace '/' on locations, i.e. 'W BROADWAY/OLIVE ST, EUG'
            # TO DO: still need to clean up city abbreviations
            location = location.replace('/', ' & ')
            
            print '''call_time: %s
            dispatch_time: %s
            incident_desc: %s 
            officers: %s 
            disposition: %s 
            event_number: %s 
            location: %s 
            priority: %s 
            case: %s ''' % (call_time, dispatch_time, incident_desc, officers, disposition, event_number, location, priority, case)
    else:
        # TO DO: What to do if it's a truncated, 250-item count ... 
        print "Truncated results"

if __name__ == "__main__" : main()
