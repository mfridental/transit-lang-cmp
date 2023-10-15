from fastapi import FastAPI
import pandas as pd
import uvicorn
import datetime as dt
import traceback

app = FastAPI()

@app.get('/schedules/{route}')
def schedules(route):
    result = []
    trip_sel = data['route_id'] == route
    filtered = data[trip_sel]
    gb = filtered.groupby(['trip_id', 'route_id', 'service_id'])
    for index, df in gb:
        try:
            tmp = df.drop(columns=['route_id', 'service_id'])
            schedule_list = tmp.to_dict('records')
            item = {
                'trip_id': index[0],
                'route_id': index[1],
                'service_id': index[2],
                'schedules': schedule_list
            }
            result.append(item)
        except:
            print(traceback.format_exc())
            print(df)
            raise
    return result

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
data = trips.join(stop_times, how='inner')
end = dt.datetime.now()
print('Prepared data in %f seconds' % (end - start).total_seconds())
print('Total startup time %f seconds' % (end - begin).total_seconds())


if __name__ == "__main__":
    #uvicorn.run(app, host="0.0.0.0", port=4000) # one worker, worst performance
    uvicorn.run("01_pandas:app", host="0.0.0.0",port=4000, workers=6) # scaling up workers

