#!/usr/bin/python

# 
# Jan. 7, 2009
# 
# Runs daily to pick up the calls from the previous day that were logged
# after midnight. (Once midnight hits, "get_epd_call_log.py" starts
# auto-inserting the current day's calls, so it misses the stragglers,
# hence the need for this script, "get_epd_call_log_backfiller.py")
# 

def main():
    import datetime
    import get_call_log
    
    yesterday = datetime.date.today() - datetime.timedelta(days = 7)
    yesterday_string = yesterday.strftime("%m/%d/%Y")
    get_call_log.main(backfill_date = yesterday_string)

if __name__ == "__main__" : main()
