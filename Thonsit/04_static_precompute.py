from fastapi import FastAPI, Response
import pandas as pd
import uvicorn
import datetime as dt
import orjson

DATA = dict()

app = FastAPI()

total_req_time = 0
requests = 0

@app.get('/schedules/{route}')
def schedules(route):
    global total_req_time, requests
    result = "[]"
    start = dt.datetime.now()

    if route in DATA:
        result = DATA[route]

    end = dt.datetime.now()
    total_req_time += (end - start).total_seconds()
    requests += 1
    print('Average request time %f seconds' % (total_req_time / requests))

    return Response(result, media_type='application/json')

start = dt.datetime.now()
begin = start
stop_times = pd.read_csv('data\\stop_times.txt')
stop_times = stop_times[['trip_id', 'stop_id', 'arrival_time', 'departure_time']]
end = dt.datetime.now()
print('Parsed stop times in %f seconds' % (end - start).total_seconds())

start = dt.datetime.now()
trips = pd.read_csv('data\\trips.txt')
trips = trips[['route_id', 'service_id', 'trip_id']]
end = dt.datetime.now()
print('Parsed trips in %f seconds' % (end - start).total_seconds())

start = dt.datetime.now()
trips.set_index('trip_id', inplace=True)
stop_times.set_index('trip_id', inplace=True)
joined = trips.join(stop_times, how='inner')

for route_id, df in joined.groupby('route_id'):
    result = []
    for (service_id, trip_id), ddf in df.groupby(['service_id', 'trip_id']):
        tmp = ddf.drop(columns=['route_id', 'service_id'])
        item = {
            'trip_id': trip_id,
            'route_id': route_id,
            'service_id': service_id,
            'schedules': tmp.to_dict('records')
        }
        result.append(item)
    DATA[route_id] = orjson.dumps(result)

trips = None
stop_times = None
joined = None
result = None
end = dt.datetime.now()
print('Prepared data in %f seconds' % (end - start).total_seconds())
print('Total generation time %f seconds' % (end - begin).total_seconds())

if __name__ == "__main__":
    uvicorn.run("04_static_precompute:app", host="0.0.0.0", port=4000, workers=6)
