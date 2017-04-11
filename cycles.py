# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
from icalendar import Calendar, Event
from jinja2 import Template
from datetime import datetime, date, timedelta
from isoweek import Week
from copy import copy
from bisect import bisect
import dateutil.parser
import pytz
import six
import json
try:
    import __builtin__ as builtins
except:
    import builtins


class Cycles(object):

    def __init__(self, constraints):
        self.WEEK = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        self.DELTAS = {self.WEEK[i]: i for i in range(len(self.WEEK))}

        constraints = self.__check(constraints)
        self.nreleases = constraints['nreleases']
        self.first_week = constraints['first_week']
        self.first_version = constraints['first_version']
        self.year = constraints['year']
        self.allowed_cycles = constraints['allowed_cycles']
        self.forbidden_weeks = constraints['forbidden_weeks']
        self.constraints = constraints['constraints']
        self.cycles = None

    def __check(self, constraints):
        def nreleases(x):
            _x = self.get_int(x)
            return _x if 1 <= _x <= 10 else 8

        def first_week(x):
            return self.get_week(x)

        def first_version(x):
            _x = self.get_int(x)
            return max(1, _x)

        def year(x):
            _x = self.get_int(x)
            return max(2000, _x)

        def allowed_cycles(x):
            _x = [6, 7, 8]
            if isinstance(x, list):
                _x = set()
                for i in x:
                    i = self.get_int(i)
                    _x.add(i if 1 <= i <= 52 else 8)
                _x = list(_x)
            return _x

        def forbidden_weeks(x):
            _x = set()
            if isinstance(x, list):
                for i in x:
                    i = self.get_int(i)
                    if 1 <= i <= 52:
                        _x.add(i)
            return _x

        def _constraints(x):
            _x = {}
            if isinstance(x, dict):
                for k, v in x.items():
                    _k = self.get_int(k)
                    if 1 <= _k <= 52:
                        _x[_k] = v

                for v in _x.values():
                    _s = set()
                    if 'diffs' in v:
                        if isinstance(v['diffs'], list):
                            for i in v['diffs']:
                                i = self.get_int(i)
                                _s.add(i if 1 <= i <= 52 else 8)
                    v['diffs'] = _s

                    _s = set()
                    if 'shifts' in v:
                        if isinstance(v['shifts'], list):
                            for i in v['shifts']:
                                i = self.get_int(i)
                                _s.add(i if -52 <= i <= 52 else 0)
                    v['shifts'] = _s
            return _x

        fmt = {'nreleases': nreleases,
               'first_week': first_week,
               'first_version': first_version,
               'year': year,
               'allowed_cycles': allowed_cycles,
               'forbidden_weeks': forbidden_weeks,
               'constraints': _constraints}

        if not isinstance(constraints, dict):
            constraints = {}

        new_constraints = {}
        for key, checker in fmt.items():
            new_constraints[key] = checker(constraints.get(key, None))

        return new_constraints

    def get_forbidden_weeks(self):
        return self.forbidden_weeks.union(self.constraints.keys())

    def generate_all_cycles(self):
        cycles = [[self.first_week]]
        for i in range(0, self.nreleases - 1):
            new_cycles = []
            for cycle in cycles:
                last_week = cycle[-1]
                for i in range(len(self.allowed_cycles)):
                    allowed = self.allowed_cycles[i]
                    # we accept only cycles where the total is less than 52
                    week = last_week + allowed
                    if week - self.first_week <= 52:
                        if week not in self.forbidden_weeks:
                            new_cycles.append(cycle + [week])
                    elif i == 0:
                        new_cycles.append(cycle)
            cycles = new_cycles
        return cycles

    def apply_constraints(self, cycles):
        good_cycles = []
        for cycle in cycles:
            good = True
            for week, constraints in self.constraints.items():
                potentially_good = False
                for shift in constraints['shifts']:
                    allowed_week = week + shift
                    # i is such that cycle[i - 1] <= allowed_week < cycle[i]
                    i = bisect(cycle, allowed_week)
                    if i >= 1 and cycle[i - 1] == allowed_week:
                        # now we need to check that difference
                        # with previous release is allowed
                        diffs = constraints['diffs']
                        if 0 in diffs:
                            potentially_good = True
                            break
                        if i >= 2:
                            diff = allowed_week - cycle[i - 2]
                            if diff in diffs:
                                potentially_good = True
                                break
                        else:
                            break
                if not potentially_good:
                    good = False
                    break

            if good:
                good_cycles.append(cycle)
        return good_cycles

    def find(self):
        cycles = self.apply_constraints(self.generate_all_cycles())
        # we have just a list of week numbers, so we need to make it clearer
        new_cycles = []
        for cycle in cycles:
            new_cycle = []
            new_cycles.append(new_cycle)
            version = self.first_version
            prev = None
            for week in cycle:
                diff = 0 if prev is None else week - prev
                prev = week
                if week <= 52:
                    year = self.year
                else:
                    year = self.year + 1
                    week -= 52

                monday = Week(year, week).monday()
                new_cycle.append({'version': version,
                                  'week': week,
                                  'monday': monday,
                                  'diff': diff})
                version += 1

        self.cycles = new_cycles

        return new_cycles

    def select(self, n):
        if self.cycles and 1 <= n <= len(self.cycles):
            cycle = self.cycles[n - 1]
            l = []
            for i in range(len(cycle)):
                c = cycle[i]
                duration = cycle[i + 1]['diff'] if i <= len(cycle) - 2 else 0
                l.append({'version': c['version'],
                          'monday': c['monday'],
                          'duration': duration})
            return l
        return []

    def get_delta_from_day(self, day):
        return self.DELTAS[day.lower()]

    def get_summary(self, event, **kwargs):
        if isinstance(event, six.string_types):
            tp = Template(event)
            return tp.render(**kwargs)
        return ''

    def merge_entries(self, normal_entry, entry):
        new_entry = {}
        for day in self.WEEK:
            ne = copy(normal_entry[day])
            new_entry[day] = ne
            e = entry.get(day, ())
            for s in e:
                if isinstance(s, six.string_types):
                    ne.append(s)
                elif isinstance(s, dict):
                    if s['action'] == 'append':
                        ne[s['position']] += s['string']
        return new_entry

    def add_entries(self, cal, monday, entry, **kwargs):
        for day in self.WEEK:
            if day in entry:
                events = entry[day]
                daydt = monday + timedelta(self.get_delta_from_day(day))
                for i in range(len(events)):
                    event = events[i]
                    summary = self.get_summary(event, **kwargs)
                    if summary:
                        e = Event()
                        e.add('summary', summary)
                        e.add('dtstart', daydt)
                        e.add('dtend', daydt)
                        cal.add_component(e)

    def get_range(self, conf):
        return sorted([self.get_int(k) for k in conf.keys() if k != 'normal'])

    def create_calendar(self, n, conf, last_beta):
        fw = self.get_forbidden_weeks()
        cal = Calendar()
        cycle = self.select(n)
        rng = self.get_range(conf)
        for i in range(len(cycle)):
            c = cycle[i]
            duration = c['duration']
            base_monday = c['monday']

            for j in rng + list(range(rng[-1] + 1, duration + rng[0])):
                if i == 0 and j < 0:
                    beta = last_beta
                if j == 1:
                    beta = 2
                index = str(j)
                monday = base_monday + timedelta(j * 7)
                week = monday.isocalendar()[1]
                if j in {-1, 0} or (i == 0 and j < 0) or week in fw:
                    # no beta here
                    if index in conf:
                        entry = conf[index]
                elif index in conf:
                    entry = self.merge_entries(conf['normal'], conf[index])
                else:
                    entry = conf['normal']
                self.add_entries(cal, monday, entry, current_beta=beta)
                if week not in fw:
                    beta += 2

        return cal

    def display(self):
        if self.cycles:
            for i in range(len(self.cycles)):
                print('Possibility %d:' % (i + 1))
                for j in range(len(self.cycles[i])):
                    c = self.cycles[i][j]
                    tuesday = self.get_date_str(c['monday'] + timedelta(1))
                    if j == 0:
                        print('Tuesday %s, week %d, ' % (tuesday, c['week']))
                    else:
                        print('Tuesday %s, week %d, (%s weeks after)' % (tuesday, c['week'], c['diff']))
                print('')

    def get_date_str(self, d):
        return d.strftime('%Y-%m-%d')

    def get_date(self, d):
        return self.as_utc(dateutil.parser.parse(d))

    def as_utc(self, d):
        if isinstance(d, datetime):
            if d.tzinfo is None or d.tzinfo.utcoffset(d) is None:
                return pytz.utc.localize(d)
            return d.astimezone(pytz.utc)
        elif isinstance(d, date):
            return pytz.utc.localize(datetime(d.year, d.month, d.day))

    def get_week(self, s):
        _s = self.get_int(s)
        if 1 <= _s <= 52:
            return _s
        try:
            return self.get_date(s).isocalendar()[1]
        except:
            return 1

    def get_int(self, x):
        _x = -1
        if (isinstance(x, six.string_types) and (x.isdigit() or (x.startswith('-') and x[1:].isdigit()))) or isinstance(x, six.integer_types):
            _x = int(x)
        return _x


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Compute cycle for Firefox releases and generate calendar')
    parser.add_argument('-c', '--constraints', action='store', default='', help='constraints filename (json)')
    parser.add_argument('-C', '--conf', action='store', default='', help='calendar configuration filename (json)')
    parser.add_argument('-l', '--lastbeta', action='store', default='', help='last beta number')
    parser.add_argument('-o', '--output', action='store', default='', help='icalendar filename')

    args = parser.parse_args()

    constraints = {}
    if args.constraints:
        with open(args.constraints, 'r') as In:
            constraints = json.load(In)

    conf = {}
    if args.conf:
        with open(args.conf, 'r') as In:
            conf = json.load(In)

    cycles = Cycles(constraints)
    pos = cycles.find()
    N = len(pos)
    cycles.display()

    if args.output:
        last_beta = int(args.lastbeta)
        select = 0
        if hasattr(builtins, 'raw_input'):
            input = getattr(builtins, 'raw_input')
        while select <= 0 or select > N:
            select = int(input('Select a possibility (1-%d): ' % N))

        cal = cycles.create_calendar(select, conf, last_beta)
        with open(args.output, 'wb') as Out:
            Out.write(cal.to_ical())
