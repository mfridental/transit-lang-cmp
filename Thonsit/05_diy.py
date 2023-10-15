from fastapi import FastAPI, Response
from fastapi.responses import ORJSONResponse
import uvicorn
import datetime as dt
import orjson
import sys
import csv

TRIPS = dict()
STOPS = dict()

app = FastAPI()

total_req_time = 0
requests = 0

@app.get('/schedules/{route}', response_class=ORJSONResponse)
def schedules(route):
    global total_req_time, requests
    result = []
    start = dt.datetime.now()

    if route in TRIPS:
        for trip in TRIPS[route]:
            item = {
                'route_id': trip.route_id,
                'service_id': trip.service_id,
                'trip_id': trip.trip_id
            }
            if trip.trip_id in STOPS:
                item['schedules'] = [{
                    'stop_id': x.stop_id,
                    'arrival_time': x.arrival_time,
                    'departure_time': x.departure_time
                } for x in STOPS[trip.trip_id]]
            result.append(item)

    end = dt.datetime.now()
    total_req_time += (end - start).total_seconds()
    requests += 1
    print('Average request time %f seconds (no json serialization)' % (total_req_time / requests))

    return ORJSONResponse(result)

class Stop:
    def __init__(self, row):
        self.trip_id = row[0]
        self.stop_id = row[3]
        self.arrival_time = row[1]
        self.departure_time = row[2]

class Trip:
    def __init__(self, row):
        self.route_id = row[0]
        self.service_id = row[1]
        self.trip_id = row[2]

start = dt.datetime.now()
begin = start


with open('data\\stop_times.txt') as f:
    reader = csv.reader(f, delimiter=',')
    checked = False
    for row in reader:
        if not checked:
            if row != ['trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence', 'stop_headsign', 'pickup_type', 'drop_off_type', 'timepoint', 'checkpoint_id', 'continuous_pickup', 'continuous_drop_off']:
                raise Exception('Unknown format of stop_times.txt')
            checked = True
        else:
            item = Stop(row)
            if not item.trip_id in STOPS:
                STOPS[item.trip_id] = list()
            STOPS[item.trip_id].append(item)
end = dt.datetime.now()
print('Parsed stop times in %f seconds' % (end - start).total_seconds())

start = dt.datetime.now()
with open('data\\trips.txt') as f:
    reader = csv.reader(f, delimiter=',')
    checked = False
    for row in reader:
        if not checked:
            if row != ['route_id', 'service_id', 'trip_id', 'trip_headsign', 'trip_short_name', 'direction_id', 'block_id', 'shape_id', 'wheelchair_accessible', 'trip_route_type', 'route_pattern_id', 'bikes_allowed']:
                raise Exception('Unknown format of stop_times.txt')
            checked = True
        else:
            item = Trip(row)
            if not item.route_id in TRIPS:
                TRIPS[item.route_id] = list()
            TRIPS[item.route_id].append(item)
end = dt.datetime.now()
print('Parsed trips in %f seconds' % (end - start).total_seconds())
print('Total generation time %f seconds' % (end - begin).total_seconds())

if __name__ == "__main__":
    uvicorn.run("05_diy:app", host="0.0.0.0", port=4000, workers=6)

