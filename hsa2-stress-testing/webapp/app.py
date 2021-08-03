import simplejson as json
import logging
import os

from decimal import Decimal
from typing import Optional, List, Mapping, Tuple

import databases
import aioredis
import sqlalchemy
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
)
logger = logging.getLogger(__name__)

MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_PORT = os.getenv('MYSQL_PORT')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')
REDIS_URL = os.getenv('REDIS_URL')

DATABASE_URL = f'mysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}'
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

items_table = sqlalchemy.Table(
    'items',
    metadata,
    sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column('title', sqlalchemy.String(length=50), nullable=False, index=True),
    sqlalchemy.Column('description', sqlalchemy.String(length=500)),
    sqlalchemy.Column('price', sqlalchemy.Numeric(precision=9, scale=2)),
)


engine = sqlalchemy.create_engine(
    f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}',
    # connect_args={'check_same_thread': False}
)
metadata.create_all(engine)

app = FastAPI()


@app.on_event('startup')
async def startup():
    await database.connect()


@app.on_event('shutdown')
async def shutdown():
    await database.disconnect()


class ItemBaseSchema(BaseModel):
    title: str
    description: Optional[str] = None
    price: Optional[Decimal]


class ItemCreateSchema(ItemBaseSchema):
    pass


class ItemSchema(ItemBaseSchema):
    id: int


class ItemsRepo:

    def __init__(self, table, db, cache):
        self._table = table
        self._db = db
        self._cache = cache
        self._cache_enabled = cache is not None

    async def create(self, item: dict) -> Mapping:
        query = self._table.insert().values(item)
        item_id = await self._db.execute(query)
        return {**item, 'id': item_id}

    async def get_by_id(self, item_id: int) -> Optional[Mapping]:
        if self._cache_enabled:
            key = f'items:{item_id}'
            ttl, value = await self._cache.get_with_ttl(key)
            if value:
                logger.info(f'get from cache: {key=}, {ttl=}')
                return json.loads(value, use_decimal=True)

            logger.info(f'get from db: {key=}')
            item = await self._fetch_item_from_db(item_id)
            value = json.dumps(dict(item))
            await self._cache.set(key, value)
            logger.info(f'set to cache: {key=}')
            return item

        return await self._fetch_item_from_db(item_id)

    async def _fetch_item_from_db(self, item_id: int) -> Optional[Mapping]:
        query = self._table.select().where(self._table.c.id == item_id)
        return await self._db.fetch_one(query)

    async def list(self, skip: int, limit: int, price_gt: int) -> List[Mapping]:
        if self._cache_enabled:
            key = f'items:{skip}-{limit}-{price_gt}'
            ttl, value = await self._cache.get_with_ttl(key)
            if value:
                logger.info(f'get from cache: {key=}, {ttl=}')
                return json.loads(value, use_decimal=True)

            logger.info(f'get from db: {key=}')
            items = await self._fetch_items_from_db(skip, limit, price_gt)
            items = [dict(item) for item in items]
            value = json.dumps(items)
            await self._cache.set(key, value)
            logger.info(f'set to cache: {key=}')
            return items

        return await self._fetch_items_from_db(skip, limit, price_gt)

    async def _fetch_items_from_db(self, skip: int, limit: int, price_gt: int) -> List[Mapping]:
        query = self._table.select()
        if price_gt > 0:
            query = query.where(self._table.c.price > price_gt)
        query = query.offset(skip).limit(limit)
        return await self._db.fetch_all(query)

    async def count_items(self) -> int:
        if self._cache_enabled:
            key = 'items-count'
            ttl, value = await self._cache.get_with_ttl(key)
            if value:
                logger.info(f'get from cache: {key=}, {ttl=}')
                return json.loads(value)

            logger.info(f'get from db: {key=}')
            res = await self._count_items_from_db()
            value = json.dumps(res)
            await self._cache.set(key, value)
            logger.info(f'set to cache: {key=}')
            return value

        return await self._count_items_from_db()

    async def _count_items_from_db(self):
        query = self._table.count()
        res = await self._db.fetch_one(query)
        return res['tbl_row_count']


class RedisCache:

    def __init__(self, redis_url: str):
        self._redis = aioredis.from_url(redis_url, decode_responses=True)

    async def get_with_ttl(self, key: str) -> Tuple[int, str]:
        async with self._redis.pipeline(transaction=True) as pipe:
            return await (pipe.ttl(key).get(key).execute())

    async def set(self, key: str, value: str, expire: int = 5):
        await self._redis.set(key, value, ex=expire)


redis_cache = RedisCache(REDIS_URL) if REDIS_URL else None
items_repo = ItemsRepo(items_table, database, redis_cache)


@app.post('/items', response_model=ItemSchema)
async def create_item(item_data: ItemCreateSchema):
    item = await items_repo.create(item_data.dict())
    return item


@app.get('/items', response_model=List[ItemSchema])
async def read_items(skip: int = 0, limit: int = 100, price_gt: int = 0):
    items = await items_repo.list(skip=skip, limit=limit, price_gt=price_gt)
    return items


@app.get('/items/{item_id}', response_model=ItemSchema)
async def read_item(item_id: int):
    item = await items_repo.get_by_id(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail='Item not found')
    return item


@app.get('/items-count')
async def count_items():
    items_count = await items_repo.count_items()
    return {'items': items_count}
