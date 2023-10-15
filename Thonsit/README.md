# Python implementations of the transit service

Python promises to develop apps quicker and easier than other programming languages, and still have an acceptable 
run-time performance.

Let's check if Python can live up to this promise.

## Naive Pandas implementation
I've decided to use Pandas to load CSV files into DataFrame and to join them together. Both operations are backed by
Pandas highly optimized, vectorized low-level programming language implementation, so they should be quick. Or so I've
thought.

Unlike the solutions for other languages, I've decided to join the two source tables together already at startup time,
because it felt to be the most Pandas way (preferring one vectorized query instead of nested table lookups).

The loading times were actually not tht bad:
```
Parsed stop times in 2.423039 seconds
Parsed trips in 0.155993 seconds
Prepared data in 0.785967 seconds
Total startup time 3.364999 seconds
```
Note that my PC has only 4 physical cores, so it not directly comparable with the M1 chip used by Gabriel Durazo. Still,
Pandas is quicker at CSV loading than Elixir, Deno and Sqlite.

Running the first performance test, with 50 VU, was very disappointing. I've got only 3,3 requests per second, with
the median request duration being 12 seconds. 
```
>k6 run -u 50 --duration 30s loadTest.js
     http_req_duration..............: avg=13.19s  min=1.02s   med=11.8s max=46.23s p(90)=20.4s   p(95)=28.35s
     http_reqs......................: 202   3.366551/s    
```
It came then to my attention that "50 VU" means that the test would issue up to 50 requests at the same time. The first
request will be handled by Python, and all subsequent requests will be waiting for the first one, because Python 
executes everything only on one core due to the GIL issue. 

So, the load test is not only measuring the performance of the search itself, but it is also very sensitive to the 
performance of basic HTTP framework as well as to availability of multi-threading.

There is a way to overcome this by spawning several child Python processes, but the FastAPI and uvicorn frameworks I am
using don't do this by default. 

After scaling it to 6 workers, I've got a slight improvement
```
>k6 run -u 50 --duration 30s loadTest.js
    http_req_duration..............: avg=4.17s   min=99.81ms med=2.81s max=43.12s   p(90)=8.28s   p(95)=12.61s
    http_reqs......................: 671    11.171/s
```
But clearly results were far from the other languages. 

## Precomputed Pandas
This solution is still using Pandas to handle data processing, but stores the pre-computed results in nested 
dictionaries:
```
route_id -> [service_id -> [trip_id -> DataFrame with stops ]]
``` 
so that the service would only need to traverse the dictionary to get the result. 
The loading time has dramatically increased to over 5 minutes, but the run-time performance has slightly improved:
```
k6 run -u 50 --duration 30s loadTest.js
     http_req_duration..............: avg=1.54s    min=3.99ms med=1.22s max=10.84s   p(90)=2.85s  p(95)=3.51s
     http_reqs......................: 1879   31.299547/s
```
At this point I was wondering, why do we need to develop a web service at all. For this specific task, we can
pre-compute everything, store the results as static JSON files and serve them, for example, with Nginx. Yes, this can't
be scaled for more complicated queries (for example with a huge number of combinations of parameters), but at this 
point I was just curious, what would be the best possible run-time performance on my hardware.

## Static precomputed files with Nginx
I'm still using Pandas to pre-render the service responses as JSON files. After that I've installed and configured
Nginx to serve those static files (see configuration example in the python script).
The generation time was around 30 seconds:
```
Parsed stop times in 2.051349 seconds
Parsed trips in 0.156989 seconds
Prepared data in 30.211794 seconds
Total generation time 32.420132 seconds
```
and the run-time performance was ok-ish:
```
>k6 run -u 50 --duration 30s loadTest.js
    http_req_duration..............: avg=31.99ms  min=0s    med=30.51ms max=179.58ms p(90)=43.03ms p(95)=49.29ms
    http_reqs......................: 48312  1538.43308/s
```
We are coming to the region with the other solutions. 1538 requests per second is quicker than 3 other contestants. But
this comparison is unfair: first, the hardware is different, and second, the python solution is too far from the other
languages, and I am not so sure whether it can be called a Python solution at all, with Nginx performing all the heavy
lifting.

On the positive note, in real-world scenarios I personally would also prefer using existing solutions like frameworks,
Nginx and databases, instead of developing everything myself, so this solution, albeit unfair, is at least pragmatic.

With only one VU, Nginx could even serve with median of 0,6 ms
```
>k6 run -u 1 --duration 30s loadTest.js
     http_req_duration..............: avg=898.53µs min=0s      med=585.79µs max=32.69ms  p(90)=1.27ms   p(95)=3.73ms
     http_reqs......................: 30987  1031.057137/s
```

## Static pre-compute in-memory
Is further improvement possible after Nginx? Can we beat Nginx performance? What if we precompute everything and store
it in memory? Nginx needs to copy data back and forth, rewrite URLs, write access.log, etc. Can further reduce the
latency by eliminating all that?

Application startup time was around 60 seconds, with the memory footprint of around 360 Mb. Run-time performance:

```
>k6 run -u 50 --duration 30s loadTest.js
     http_req_duration..............: avg=47.42ms  min=509.49µs med=40.04ms max=254.03ms p(90)=87.44ms p(95)=105.4ms
     http_reqs......................: 33462  1026.131002/s
```
No, we can't beat Nginx, at least not with Python. But it is nice to see that a python app can achieve similar latency 
than a static web site served by Nginx.

The web service is measuring its own performance in this solution (except of the JSON serialization) and it comes to 
2 µs per search, on average. Basically, we're at the point now, where we measure mostly noise, such as sudden 
invocation of other processes running on the same hardware, GC effects, etc., so it is time to stop optimizing the latency.

Now, at the latest, you might be wondering if any of these implementations are comparable with solutions in other
programming languages, at all, because the algorithms are quite different.

So I've decided to re-implement the Rust / C# solution, in Python, as closely as feasible, and give it a try.

## DIY
So what actually happens, if you would use Python as if it was Rust or C#?
Application load time is slower than other languages, but it is not really terrible, at all:
```
Parsed stop times in 5.046259 seconds
Parsed trips in 0.189993 seconds
Total generation time 5.236252 seconds
```
Hmm, why did I use Pandas before? A typical case of premature optimization perhaps.
Now, the run-time performance:
```
>k6 run -u 50 --duration 30s loadTest.js
     http_req_duration..............: avg=285.73ms min=1.95ms med=221.3ms max=4.37s    p(90)=509.86ms p(95)=631.63ms
     http_reqs......................: 6534   156.469229/s
```
It is slower than the slowest tested language. And it's only 10% of C#. Everything as expected here. Don't use Python 
like this.

Finally, let's implement the actual goal of the software. Gabriel mentioned in the requirements that he wants it to be
extendable for other kinds of searches in the future. Basically, this it the reason why other solutions wouldn't pre-
compute everything to the final JSON reponse of the service, but rather keep data more or less decoupled from the
service (if you ignore the presense of indexes).

Well, in the Python world, the typical solution to this goal would be a database. Like Crocodile Dundee would say,
hashtables and pointers and self-implemented indexes? That's not a knife! A mature, embedded, SQL, analytical 
database - that's a knife! 


## Duck DB
Application startup time for one worker process:
```
Parsed stop times in 0.814005 seconds
Parsed trips in 0.141963 seconds
Total generation time 0.955968 seconds
```
Don't be fooled by these very quick and nice numbers: as Duck DB uses all available cores when working, the startup 
time must be multiplied by the number of worker processes. Here is where a real hardware multithreading would come
handy for python developers, because then we wouldn't need to load data into each worker process separately.

But yet again, another solution might be a new feature for Duck DB to use memory shared by several processes for in-memory
database. Let the system developers make heavy lifting for us.

So how does it look with performance? Because Duck DB uses all CPU cores for each query, it doesn't make sense to make
more than 1 VU (unless we want to be disappointed):
```
>k6 run -u 1 --duration 30s loadTest.js
     http_req_duration..............: avg=89.48ms min=3.41ms med=72ms     max=338.13ms p(90)=168.52ms p(95)=216.26ms
     http_reqs......................: 396    11.154755/s
```
we can see some nice latency (I frankly haven't expected that an analytical SQL database can respond on real data 
quicker than for 100ms) but a very low throughput (because we've maxed out all CPUs).

So achieve 2000 requests per second, we would need to deploy the service to 50 nodes, each having 16 cores. It will
be expensive, but well, this is the price of real flexibility, if we want our service to be both ultimately flexible,
have low latency and high throughput. 

On the positive note, you can calculate virtually everything with Duck DB. Just look and their function reference. 
Want to add standard deviation of the time between arrival and departure? That would be exactly one line of code more, 
and barely slower.

## Precomputed Duck DB
We can also use Duck DB to load CSV data and to pre-compute the results for the service. This would minimize development
time, maximize flexibility*, and minimize latency.

Application startup time is around 9 seconds, multiplied by the number of workers, and the memory footprint of the 
worker processes is around 190 Mb.

Load testing with the usual 50 VU:
```
>k6 run -u 50 --duration 30s loadTest.js
     http_req_duration..............: avg=16.38ms  min=507.29µs med=12.79ms max=146.5ms  p(90)=31.68ms p(95)=39.2ms
     http_reqs......................: 76230  1270.345909/s
```
I have increased then to 10 worker processes, which has improved performance despite having only 4 physical cores:
```
>k6 run -u 50 --duration 30s loadTest.js
     http_req_duration..............: avg=21.27ms  min=506.9µs  med=17.5ms  max=251.09ms p(90)=40.14ms p(95)=50.25ms
     http_reqs......................: 71874  2302.415184/s
```
Further increase to 16 workers:
```
>k6 run -u 50 --duration 30s loadTest.js
     http_req_duration..............: avg=19.77ms  min=462.6µs  med=13.59ms max=340.92ms p(90)=45.7ms  p(95)=60.57ms
     http_reqs......................: 76725  2469.54445/s
```

On this satisfying note I would like to conclude my optimizations. The requests per seconds are now comparable to
Rust, and the latency is more than acceptable.

(*) caveat: like mentioned above, the flexibility is provided only for pre-computable searches.

## Summary and Discussion

1) A Python solution, using only python frameworks, has achieved the run-time performance probably comparable 
to Rust, on a probably inferior hardware.

2) The Python solution needs only 54 lines of code, while Rust needs 213, Go needs 183, Deno needs 146, C# needs 213.

3) Python needs a different software development style. Data structures, indexes, parsing, serializing to JSON are 
system-level functions. Choosing what fields to use for joining, what fields to include to result set and how to react
on errors are application-level functions. Writing everything a) in the same programming language and b) by yourself is 
a DIY style similar to building a house brick by brick on site. Using SQL and Python for application logic and 
frameworks implemented in low-level languages for system-level functions is another style, similar to building a house
with pre-manufactured concrete panels. Both styles have their advantages and disadvantages. DIY has unlimited 
flexibility but high development costs and long time to market. On the other hand, mass-production is limited to 
standard floor plans, but is cheaper and can be finished in 24 hours.

4) In this particular case, if in the future a query will be needed that cannot be feasibly precomputed (eg. substring
search in the route_id), the Python solution would either need to be deployed to a cluster with a high number of CPU
cores to produce the same latency and throughput, or the users have to accept that the search takes a couple of seconds 
instead of a dozen of milliseconds.

5) The load test is not only measuring the performance of the search itself, but it is also very sensitive to the 
performance of basic HTTP framework as well as to availability of multi-threading. Some programming languages might 
include HTTP frameworks that would use every CPU core automatically and even spawn more threads than cores hoping for
performance advantages due to pre-emptive green threads, while other programming languages might be less aggressive. 
With the 50 VU we're definitely in the range where we are mostly measuring the quality of the HTTP stack. Python is
especially bad here with its GIL.

6) The load test is sensitive to the number and speed of the physical cores. For comparable benchmarks, all solutions
should be tested on the same hardware.

7) The solutions in other languages have a fixed flexibility level, where some pre-computations take place, but the 
service is neither 100% pre-computed nor fully flexible. This chosen level of flexibility leaves Python to be the 
slowest competitor. It would be interesting to see an implementation of a Rust solution that would fully pre-compute 
the result, as well as a Rust solution that would use Duck DB to achieve full flexibility.

## Lessons Learned
- FastAPI and uvicorn serve by default only one request at a time. Installing an Nginx in front of several FastAPI
worker processes won't help, because Nginx would occasionally send more than one request per worker simultaneously.
- uvicorn has a parameter "workers" and can spawn them automatically.
- orjson is measurably much quicker than the standard json framework
- Duck DB is faster than Pandas, but uses all CPU cores (Pandas uses only one). It also has very cool functions and
data types.
- Don't try to beat Nginx performance with Python
- Don't try to program in Python as if it was C / Rust / Go / C#. Every time you find yourself writing a loop, ask
yourself if there is any python framework (implemented in a low-level language) that will do the job quicker.
- k6 is a cool load testing tool that is not limited to HTTP(S)

## How to run
1) Download the data and extract and place trips.txt and stop_times.txt in subdirectory "data"
2) ```python -m venv venv```
3) ```./venv/bin/activate```
4) ```pip install -r requirements.txt```
5) ```python 07_duckdb_precomputed.py```

(c) Maxim Fridental