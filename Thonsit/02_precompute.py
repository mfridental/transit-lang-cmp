from fastapi import FastAPI
import pandas as pd
import uvicorn
import datetime as dt
from fastapi.responses import ORJSONResponse

start = dt.datetime.now()
begin = start
stop_times = pd.read_csv('data\\stop_times.txt')
stop_times = stop_times[['trip_id', 'stop_id', 'arrival_time', 'departure_time']]
end = dt.datetime.now()
print('Parsed stop times in %f seconds' % (end-start).total_seconds())

start = dt.datetime.now()
trips = pd.read_csv('data\\trips.txt')
trips = trips[['route_id', 'service_id', 'trip_id']]
end = dt.datetime.now()
print('Parsed trips in %f seconds' % (end-start).total_seconds())

start = dt.datetime.now()
trips.set_index('trip_id', inplace=True)
stop_times.set_index('trip_id', inplace=True)
joined = trips.join(stop_times, how='inner')
grouped = joined.groupby(['route_id', 'service_id', 'trip_id'])
print('Number of combinations %d' % len(grouped.size()))
schedules_data = dict()
i = 0
for (route_id, service_id, trip_id), df in grouped:
    if route_id not in schedules_data:
        schedules_data[route_id] = {}
    if service_id not in schedules_data[route_id]:
        schedules_data[route_id][service_id] = {}
    tmp = df.drop(columns=['route_id', 'service_id'])
    schedules_data[route_id][service_id][trip_id] = tmp
    i += 1
    if i % 1000 == 0:
        print('%d done' % i)
print('%d done' % i)
end = dt.datetime.now()
print('Prepared data in %f seconds' % (end-start).total_seconds())
print('Total startup time %f seconds' % (end-begin).total_seconds())

app = FastAPI()

total_req_time = 0
requests = 0

@app.get('/schedules/{route}', response_class=ORJSONResponse)
def schedules(route):
    global total_req_time, requests
    result = []
    start = dt.datetime.now()

    if route in schedules_data:
        for service_id, vv in schedules_data[route].items():
            for trip_id, df in vv.items():
                result.append({
                    'trip_id': trip_id,
                    'route_id': route,
                    'service_id': service_id,
                    'schedules': df.to_dict('records')
                })

    end = dt.datetime.now()
    total_req_time += (end - start).total_seconds()
    requests += 1
    print('Average request time %f seconds' % (total_req_time / requests))

    return ORJSONResponse(result)

if __name__ == "__main__":
    import sys
    uvicorn.run("02_precompute:app", host="0.0.0.0", port=4000, workers=6)
