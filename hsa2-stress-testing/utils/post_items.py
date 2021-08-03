import argparse

import uvloop
uvloop.install()

import asyncio
import logging
import random

import aiohttp
import faker

URL = 'http://localhost:8000/items'
FAKER = faker.Faker()

logger = logging.getLogger(__name__)


async def post_item(
        queue: asyncio.Queue,
        session: aiohttp.ClientSession,
):
    c = 0
    while item := await queue.get():
        async with session.post(URL, json=item) as resp:
            if not resp.ok:
                text = await resp.text()
                logger.error(f'{text=}')
                continue
            c += 1

        if c % 100 == 0:
            logger.info('posted 100 items..')


async def main(items_num: int, workers_num: int = 10):
    logger.info(f'Creating {items_num} items, using {workers_num} workers')

    queue = asyncio.Queue()
    async with aiohttp.ClientSession() as session:
        workers = [
            asyncio.create_task(post_item(queue, session))
            for _ in range(workers_num)
        ]

        for _ in range(items_num):
            await queue.put(
                {
                    'title': FAKER.text()[:random.randint(10, 50)],
                    'description': FAKER.text()[:500],
                    'price': FAKER.random_int(),
                },
            )

        for _ in range(workers_num):
            await queue.put(None)

        await asyncio.gather(*workers)

    logger.info('Success')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument('items_num', type=int)
    parser.add_argument('--workers', default=10, type=int)
    args = parser.parse_args()

    asyncio.run(main(args.items_num, args.workers))
