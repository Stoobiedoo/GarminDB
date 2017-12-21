#!/usr/bin/env python

#
# copyright Tom Goetz
#

import os, sys, getopt, re, string, logging, datetime

import GarminSqlite


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
#logger.setLevel(logging.DEBUG)


class Analyze():

    def __init__(self, dbpath):
        self.garmindb = GarminSqlite.GarminDB(dbpath)
        self.mondb = GarminSqlite.MonitoringDB(dbpath)
        self.sumdb = GarminSqlite.MonitoringSummaryDB(dbpath)
        units = GarminSqlite.Attributes.find_one(self.garmindb, {'name' : 'units'})
        if units.value == 'english':
            self.english_units = True
        else:
            self.english_units = False

    def get_years(self):
        years = GarminSqlite.Monitoring.get_years(self.mondb)
        GarminSqlite.Summary.create_or_update(self.sumdb, {'name' : 'years', 'value' : len(years)})
        print "Years (%d): %s" % (len(years), str(years))

    def get_months(self, year):
        months = GarminSqlite.Monitoring.get_month_names(self.mondb, year)
        GarminSqlite.Summary.create_or_update(self.sumdb, {'name' : year + '_months', 'value' : len(months)})
        print "%s Months (%d): %s" % (year, len(months) , str(months))

    def get_days(self, year):
        year_int = int(year)
        days = GarminSqlite.Monitoring.get_days(self.mondb, year)
        days_count = len(days)
        if days_count > 0:
            first_day = days[0]
            last_day = days[-1]
            span = last_day - first_day + 1
        else:
            span = 0
        GarminSqlite.Summary.create_or_update(self.sumdb, {'name' : year + '_days', 'value' : days_count})
        GarminSqlite.Summary.create_or_update(self.sumdb, {'name' : year + '_days_span', 'value' : span})
        print "%d Days (%d vs %d): %s" % (year_int, days_count, span, str(days))
        for index in xrange(days_count - 1):
            day = int(days[index])
            next_day = int(days[index + 1])
            if next_day != day + 1:
                day_str = str(GarminSqlite.day_of_the_year_to_datetime(year_int, day))
                next_day_str = str(GarminSqlite.day_of_the_year_to_datetime(year_int, next_day))
                print "Days gap between %d (%s) and %d (%s)" % (day, day_str, next_day, next_day_str)

    def summary(self):
        years = GarminSqlite.Monitoring.get_years(self.mondb)
        for year in years:
            days = GarminSqlite.Monitoring.get_days(self.mondb, year)
            for day in days:
                day_ts = datetime.datetime(year, 1, 1) + datetime.timedelta(day - 1)
                stats = GarminSqlite.MonitoringHeartRate.get_daily_stats(self.mondb, day_ts)
                stats.update(GarminSqlite.MonitoringClimb.get_daily_stats(self.mondb, day_ts, self.english_units))
                stats.update(GarminSqlite.MonitoringIntensityMins.get_daily_stats(self.mondb, day_ts))
                stats.update(GarminSqlite.Monitoring.get_daily_stats(self.mondb, day_ts))
                GarminSqlite.DaysSummary.create_or_update(self.sumdb, stats)
            for week_starting_day in xrange(1, 365, 7):
                day_ts = datetime.datetime(year, 1, 1) + datetime.timedelta(week_starting_day - 1)
                stats = GarminSqlite.MonitoringHeartRate.get_weekly_stats(self.mondb, day_ts)
                stats.update(GarminSqlite.MonitoringClimb.get_weekly_stats(self.mondb, day_ts, self.english_units))
                stats.update(GarminSqlite.MonitoringIntensityMins.get_weekly_stats(self.mondb, day_ts))
                stats.update(GarminSqlite.Monitoring.get_weekly_stats(self.mondb, day_ts))
                GarminSqlite.WeeksSummary.create_or_update(self.sumdb, stats)


def usage(program):
    print '%s -d <dbpath> -m ...' % program
    sys.exit()

def main(argv):
    dbpath = None
    years = False
    months = None
    days = None
    summary = False

    try:
        opts, args = getopt.getopt(argv,"d:i:m:sy", ["dbpath=", "days=", "months=", "years", "summary"])
    except getopt.GetoptError:
        usage(sys.argv[0])

    for opt, arg in opts:
        if opt == '-h':
            usage(sys.argv[0])
        elif opt in ("-d", "--dbpath"):
            logging.debug("DB path: %s" % arg)
            dbpath = arg
        elif opt in ("-y", "--years"):
            logging.debug("Years")
            years = True
        elif opt in ("-m", "--months"):
            logging.debug("Months")
            months = arg
        elif opt in ("-d", "--days"):
            logging.debug("Days")
            days = arg
        elif opt in ("-s", "--summary"):
            logging.debug("Summary")
            summary = True

    if not dbpath:
        print "Missing arguments:"
        usage(sys.argv[0])

    analyze = Analyze(dbpath)
    if years:
        analyze.get_years()
    if months:
        analyze.get_months(months)
    if days:
        analyze.get_days(days)
    if summary:
        analyze.summary()

if __name__ == "__main__":
    main(sys.argv[1:])

