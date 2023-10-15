from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
import uvicorn
import datetime as dt
import duckdb

app = FastAPI()

total_req_time = 0
requests = 0

@app.get('/schedules/{route}', response_class=ORJSONResponse)
def schedules(route):
    global total_req_time, requests, db
    start = dt.datetime.now()

    cur = db.cursor()
    cur.execute("""
        SELECT {
            'route_id': route_id, 
            'service_id': service_id, 
            'trip_id': Trips.trip_id, 
            'schedules': list({
                'stop_id': stop_id, 
                'arrival_time': arrival_time, 
                'departure_time': departure_time                
            })
        }
        from Trips
        join StopTimes on Trips.trip_id = StopTimes.trip_id 
        where route_id='%s'
        group by route_id, service_id, Trips.trip_id        
        """ % route)
    result = [x[0] for x in cur.fetchall()]

    end = dt.datetime.now()
    total_req_time += (end - start).total_seconds()
    requests += 1
    print('Average request time %f seconds (no json serialization)' % (total_req_time / requests))

    return ORJSONResponse(result)


start = dt.datetime.now()
begin = start
db = duckdb.connect(':memory:')

db.sql("""CREATE TABLE StopTimes AS FROM read_csv_auto('data\\stop_times.txt', all_varchar=1)""")
end = dt.datetime.now()
print('Parsed stop times in %f seconds' % (end - start).total_seconds())

start = dt.datetime.now()
db.sql("""CREATE TABLE Trips AS FROM read_csv_auto('data\\trips.txt', all_varchar=1)""")
end = dt.datetime.now()
print('Parsed trips in %f seconds' % (end - start).total_seconds())
print('Total generation time %f seconds' % (end - begin).total_seconds())

if __name__ == "__main__":
    uvicorn.run("06_duckdb:app", host="0.0.0.0", port=4000, workers=6)


