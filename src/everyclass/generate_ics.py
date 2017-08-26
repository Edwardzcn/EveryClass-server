import pytz
import re
from icalendar import Calendar, Event, Alarm
from datetime import datetime, timedelta
from config import load_config
from commons import get_time


# .ics files should follow
# https://tools.ietf.org/html/rfc2445?cm_mc_uid=02098050116114871518159&cm_mc_sid_50200000=1493972416
def generate_ics(student_id, student_name, student_classes, semester_string, semester):
    # Create calender object
    cal = Calendar()
    cal.add('prodid', '-//Admirable//EveryClass 1.0//EN')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('X-WR-CALNAME', student_name + '的课表')
    cal.add('X-WR-TIMEZONE', 'Asia/Shanghai')
    # Create events
    for time in range(1, 7):
        for day in range(1, 8):
            if (day, time) in student_classes:
                for every_class in student_classes[(day, time)]:
                    # 每一节课
                    durations = re.split(r',', every_class['duration'])
                    for each_duration in durations:
                        # 每一段上课周
                        if len(re.findall(r'\d{1,2}', each_duration)) == 1:  # 仅当周
                            dur_starting_week = dur_ending_week = re.findall(r'\d{1,2}', each_duration)[0]
                        else:  # X 到 X 周
                            dur_starting_week, dur_ending_week = re.findall(r'\d{1,2}', each_duration)
                        if every_class['week'] == '周':
                            interval = 1
                        else:
                            interval = 2
                        if every_class['week'] == '双周' and int(dur_starting_week) % 2 != 0:
                            dur_starting_week += str(int(dur_starting_week)+1)
                        if every_class['week'] == '单周' and int(dur_starting_week) % 2 == 0:
                            dur_starting_week += str(int(dur_starting_week)+1)
                        dtstart = __get_datetime(dur_starting_week, day, get_time(time)[0], semester)
                        dtend = __get_datetime(dur_starting_week, day, get_time(time)[1], semester)
                        until = __get_datetime(dur_ending_week, day, get_time(time)[1], semester) + timedelta(days=1)
                        # 参数：课程名称、初次时间[start、end、interval、until、duration]、循环规则、地点、老师、学生 ID
                        cal.add_component(
                            __add_event(every_class['name'],
                                        [dtstart, dtend, interval, until, each_duration, every_class['week']],
                                        every_class['location'],
                                        every_class['teacher'], student_id))
    # Write file
    import os
    with open(os.path.dirname(__file__) + '/ics/%s-%s.ics' % (student_id, semester_string), 'w') as f:
        f.write(cal.to_ical().decode(encoding='utf-8'))


# 输入周次，星期、时间tuple（时,分），输出datetime类型的时间
def __get_datetime(week, day, time, semester):
    return datetime(*load_config().AVAILABLE_SEMESTERS.get(semester)['start'], *time,
                    tzinfo=pytz.timezone("Asia/Shanghai")) + timedelta(days=(int(week) - 1) * 7 + (int(day) - 1))


# Add event
def __add_event(name, times, location, teacher, student_id):
    event = Event()
    event.add('transp', 'TRANSPARENT')
    summary = name
    if location != 'None':
        summary = name + '@' + location
        event.add('location', location)
    description = times[4] + times[5]
    if teacher != 'None':
        description += '\n教师：' + teacher + '\n'
    description += '由 EveryClass (https://every.admirable.one) 导入'
    event.add('summary', summary)
    event.add('description', description)
    event.add('dtstart', times[0])
    event.add('dtend', times[1])
    event.add('last-modified', datetime.now())
    event['uid'] = 'ec-CSU' + student_id + 't' + datetime.now().strftime('%y%m%d%H%M%S%f') + '@admirable.one'
    event.add('rrule', {'freq': 'weekly', 'interval': times[2],
                        'until': times[3]})
    alarm = Alarm()
    alarm.add('action', 'none')
    alarm.add('trigger', datetime(1980, 1, 1, 3, 5, 0))
    event.add_component(alarm)
    return event
