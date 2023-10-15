from fastapi import FastAPI, Response
import uvicorn
import datetime as dt
import duckdb
import orjson

app = FastAPI()

DATA = dict()

@app.get('/schedules/{route}')
def schedules(route):
    result = "[]"
    if route in DATA:
        result = DATA[route]
    return Response(result, media_type='application/json')

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

start = dt.datetime.now()
db.execute("""
SELECT route_id, {
        'route_id': route_id, 
        'service_id': service_id, 
        'trip_id': Trips.trip_id, 
        'schedules': list({
            'stop_id': stop_id, 
            'arrival_time': arrival_time, 
            'departure_time': departure_time                
        })
    } as response
    from Trips
    join StopTimes on Trips.trip_id = StopTimes.trip_id 
    group by route_id, service_id, Trips.trip_id            
""")
for row in db.fetchall():
    DATA[row[0]] = orjson.dumps(row[1])
db.close()
end = dt.datetime.now()
print('Preaggregated data in %f seconds' % (end - start).total_seconds())
print('Total generation time %f seconds' % (end - begin).total_seconds())

if __name__ == "__main__":
    uvicorn.run("07_duckdb_precompute:app", host="0.0.0.0", port=4000, workers=16)