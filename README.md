## Prerequisites
- docker
- docker-compose
- ab

## Start

```commandline
docker-compose up
```

### Testing GET of single resource
```commandline
ab -n 10000 -c 10 http://127.0.0.1:8000/items/60f176c4e16149fc16013e4b
```

### Testing GET of resources list
```commandline
ab -n 10000 -c 10 http://127.0.0.1:8000/items
```


### Open Grafana to review containers metrics 
http://localhost:3000


### Api docs
http://localhost:8000/docs
