from django.core import serializers
from cal.models import Event, RepeatEvent, BreakEvent
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import datetime
import re
import itertools


# ------------------------------------------------------------------------
# Gets events, and RepeatEvents from the user's database. Merges them into
# one json and sends the result
# ------------------------------------------------------------------------
def get_events(request):
    # get events for user
    user = request.user
    events = user.event_set.all()
    repeat_events = user.repeatevent_set.all()
    all_events = itertools.chain(events, repeat_events)

    # convert event data to JSON
    json_data = serializers.serialize('json', all_events, use_natural_keys=True)
    return HttpResponse (json_data, mimetype='application/json')


# ------------------------------------------------------------------------
# Adds Event object to database. Returns the id given to the new object.
# ------------------------------------------------------------------------
@csrf_exempt
def add_event(request):
    # get new event data
    user = request.user
    title = request.POST['title']
    start = strToDateTime(request.POST['start'])
    end = strToDateTime(request.POST['end'])
    allDay = True if (request.POST['allDay'] == 'true') else False

    # make new event and save
    event = Event(
        user = user,
        title=title,
        start=start,
        end=end,
        allDay=allDay
    )
    event.save()

    # return the id of the new event
    return HttpResponse(str(event.id))


# ------------------------------------------------------------------------
# Adds RepeatEvent object to database. Returns the id given to the new object.
# ------------------------------------------------------------------------
@csrf_exempt
def add_repeat(request):
    # get new event data
    user = request.user
    title = request.POST['title']
    start = strToDateTime(request.POST['start'])
    end = strToDateTime(request.POST['end'])
    allDay = True if (request.POST['allDay'] == 'true') else False

    # make new RepeatEvent and save
    event = RepeatEvent(
        user = user,
        title=title,
        start=start,
        end=end,
        allDay=allDay
    )
    event.save()

    # return the id of the new event
    return HttpResponse(str(event.id))


# ------------------------------------------------------------------------
# Remove Event object from database
# ------------------------------------------------------------------------
@csrf_exempt
def delete_event(request):
    # get event id
    user = request.user
    id = request.POST['sid']

    # delete event
    user.event_set.get(pk = id).delete()
    return HttpResponse("Okay")



# ------------------------------------------------------------------------
# Has the effect of deleting the current and future events from a RepeatEvent
# chain. In the database it simply adds an end date on the RepeatEvent unless
# the end date is the head, in which case it deletes the RepeatEvent
# ------------------------------------------------------------------------
@csrf_exempt
def delete_repeat(request):
    # get event id and user
    user = request.user
    id = request.POST['sid']
    date = strToDateTime(request.POST['start'])

    # container for httpresponse
    idreturn = ''

    # get RepeatEvent object
    repeat = user.repeatevent_set.get(pk = id)

    # check whether date is at the head
    if date == repeat.start:
        # delete RepeatEvent
        repeat.delete()
    # check if you are one past the head
    elif oneBack(date, 'rrule') == repeat.start:
        # make the head into a new Event object
        event = Event(
            user = user,
            title=repeat.title,
            start=repeat.start,
            end=repeat.end,
            allDay=repeat.allDay
        )
        event.save()
        idreturn = str(event.id)

        # delete RepeatEvent
        repeat.delete()
    # otherwise
    else:
        # set end date to one instance back of the passed in date
        end = oneBack(date, 'ruleHere')
        # update repeat and save
        repeat.endRepeat = end
        repeat.save()

    # return id of new event that was made at the head
    return HttpResponse(idreturn)



# ------------------------------------------------------------------------
# Called only when an Event object is edited. Update the fields for the event
# in the database.
# ------------------------------------------------------------------------
@csrf_exempt
def edit_event(request):
    # get new event data
    user = request.user
    id = request.POST['sid']
    title = request.POST['title']
    start = strToDateTime(request.POST['start'])
    end = strToDateTime(request.POST['end'])
    allDay = True if (request.POST['allDay'] == 'true') else False

    # get event to update
    event = user.event_set.get(pk = id)

    # update elements and save
    event.title = title
    event.start = start
    event.end = end
    event.allDay = allDay
    event.save()

    return HttpResponse("Okay")


# ------------------------------------------------------------------------
# Called when a RepeatEvent is edited and applied to all future events.
# Must be given event_orig and event_new for the event that was edited.
# Add an end date on the RepeatEvent object based on the event_orig date.
# Then create a new RepeatEvent object based on the event_new date.
# ------------------------------------------------------------------------
@csrf_exempt
def edit_repeat(request):
    user = request.user
    id = request.POST['sid']
    oldStart = strToDateTime(request.POST['oldStart'])
    newStart = strToDateTime(request.POST['start'])
    newEnd = strToDateTime(request.POST['end'])

    # get old RepeatEvent object
    repeat = user.repeatevent_set.get(pk = id)
    breaks = repeat.breaks.all()

    # get break events to move to new repeatevent
    breaks_new = []
    for br in breaks:
        if br.date > oldStart:
            # remove from old repeat
            repeat.breaks.remove(br)
            # save to breaks_new array
            breaks_new.append(br)

    # container to hold httpresponse of ids
    ids = ''

    # check whether oldStart is the head
    if oldStart == repeat.start:
        # delete RepeatEvent
        repeat.delete()
    # check if you are one past the head
    elif oneBack(oldStart, 'rrule') == repeat.start:
        # make the head into a new Event object
        event = Event(
            user = user,
            title=repeat.title,
            start=repeat.start,
            end=repeat.end,
            allDay=repeat.allDay
        )
        event.save()
        # add id to container
        ids = str(event.id) + ','
        # delete RepeatEvent
        repeat.delete()
    # otherwise
    else:
        # set end date to one instance back of the passed in date
        end = oneBack(oldStart,'rrule')
        # update repeat and save
        repeat.endRepeat = end
        repeat.save()

    # create new RepeatEvent object based on new datetimes
    new_repeat = RepeatEvent(
        user = user,
        title=request.POST['title'],
        start=newStart,
        end=newEnd,
        allDay=request.POST['allDay']
    )
    new_repeat.save()

    # add id to container
    ids += str(new_repeat.id)

    # move breaks to new chain by delta
    delta = newStart - oldStart
    for br in breaks_new:
        br.date += delta
        br.save()
        new_repeat.breaks.add(br)

    # '3' OR '1,3' where first number is the event id for the head and second is id of new RepeatEvent
    return HttpResponse(ids)


# ------------------------------------------------------------------------
# Called for a RepeatEvent object when 'just this' date is deleted. Simply
# adds a BreakEvent for the RepeatEvent current object
# ------------------------------------------------------------------------
@csrf_exempt
def break_repeat(request):
    # get event id
    user = request.user
    id = request.POST['sid']
    date = strToDateTime(request.POST['start'])

    # get the RepeatEvent object
    repeat = user.repeatevent_set.get(pk = id)

    # add a BreakEvent to repeat
    new_break = BreakEvent(date=date)
    new_break.save()
    repeat.breaks.add(new_break)

    return HttpResponse("Okay")


# ------------------------------------------------------------------------
# NOT including the present object, this converts a RepeatEvent object from its
# head until the inputted date into all Event objects. Returns csv of new ids
# from head to tail
# ------------------------------------------------------------------------
@csrf_exempt
def free_repeat(request):
    # get information
    user = request.user
    event_start = strToDateTime(request.POST['start']) # last date to free (starting from head)
    event_end = strToDateTime(request.POST['end'])
    id = request.POST['sid']
    title = request.POST['title']
    allDay = True if (request.POST['allDay'] == 'true') else False

    # calculate the event length if an end exists
    if event_end:
        event_length = event_end - event_start

    # get the RepeatEvent object
    repeat = user.repeatevent_set.all().get(pk = id)
    head = repeat.start

    # format the breaks array
    breaks = []
    for _break in repeat.breaks.all():
        breaks.append(_break.date)

    # delete the RepeatEvent object
    repeat.delete()

    # TODO! get rrule from repeat object

    # loop from head to event_start, making new Event objects
    cursor = head
    ids = ''
    while cursor < event_start:
        # check if current date is a break
        if cursor in breaks:
            continue

        # make new event and save
        event = Event(
            user=user,
            title=title,
            start=cursor,
            end=cursor,
            allDay=allDay
        )
        # add length of event if it exists
        if event_end:
            event.end += event_length
        event.save()

        # add id to ids csv string
        ids += str(event.id) + ','

        # move cursor
        cursor = oneForward(cursor, 'rrule')

    # remove last comma
    ids = ids[:-1]

    return HttpResponse(ids)



# ------------------------------------------------------------------------
# Takes in string with format "Fri Nov 16 2012 00:00:00 GMT-0500 (EST)"
# and converts it to a DateTime object. Returns None on no match
# ------------------------------------------------------------------------
def strToDateTime(string):
    # pattern to strip "GMT-0500 (EST)"
    pattern = re.compile('.*\d{2}:\d{2}:\d{2}')

    # Return datetime object upon match, otherwise None
    if pattern.search(string):
        string2 = pattern.search(string).group(0)
        return datetime.datetime.strptime(string2, "%a %b %d %Y %H:%M:%S")
    else:
        return None


# ------------------------------------------------------------------------
# Functions that take in a DateTime object and return a DateTime object of
# the next or previous date according to a given repeat rule string
# ------------------------------------------------------------------------
def oneBack(date, rrule):
    return date - datetime.timedelta(days=7)

def oneForward(date, rrule):
    return date + datetime.timedelta(days=7)