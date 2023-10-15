import pandas as pd
import datetime as dt
import os
import orjson

"""
This script just generates statis JSON files and stores them into ./nginx/html/schedules folder.

Use the following nginx.conf file:

worker_processes  4;

events {
    worker_connections  8096;
    multi_accept        on;
}

worker_rlimit_nofile 40000;

http {
    include       mime.types;
    default_type  application/octet-stream;

    sendfile        on;
    tcp_nopush         on;
    tcp_nodelay        on;
    keepalive_timeout  15;

    server {
        listen       4000;
        server_name  localhost;

        location / {
            root html;
            rewrite ^/schedules/(.*)$ \schedules\$1.json;
            sendfile           on;
            tcp_nopush on;
        }

        error_page   500 502 503 504  /50x.html;
        location = /50x.html {
            root   html;
        }
    }
}

"""

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

for route_id, df in joined.groupby('route_id'):
    with open(os.path.join('nginx', 'html', 'schedules', route_id+'.json'), 'wb') as f:
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
        f.write(orjson.dumps(result))

end = dt.datetime.now()
print('Prepared data in %f seconds' % (end-start).total_seconds())
print('Total generation time %f seconds' % (end-begin).total_seconds())
