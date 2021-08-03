## hsa2-stress-testing:

1) Comment `REDIS_URL` in webapp service env and start all containers using
`docker-compose up -d`
2) Post some payload using `python utils/post_items.py 10000`
3) Generate urls list using `python utils/generate_urls.py 10000`
4) Run siege benchmarks using `siege -b -c<CONC> -t60s -f utils/urls.txt` for different CONC values (10, 25, 50, 100 etc.)
5) Uncomment `REDIS_URL` in webapp service and restart it using `docker-compose up -d webapp`
6) Rerun siege benchmarks and analyze received results