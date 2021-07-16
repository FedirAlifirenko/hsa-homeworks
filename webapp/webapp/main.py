import asyncio
import os
from typing import Optional

import bson.errors
from bson import ObjectId
from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

MONGODB_ADDRESS = os.getenv('MONGODB_ADDRESS', 'mongodb://localhost:27017')
ES_HOST = os.getenv('ES_HOST', 'elasticsearch')
ES_PORT = int(os.getenv('ES_PORT', 9200))
ES_ITEMS_INDEX = 'items'
WAIT_ES_SECONDS = 10

app = FastAPI()

es = AsyncElasticsearch(hosts=[{'host': ES_HOST, 'port': ES_PORT}])
client = AsyncIOMotorClient(MONGODB_ADDRESS)
db = client.test


@app.on_event("startup")
async def app_startup():
    success = False
    for _ in range(WAIT_ES_SECONDS):
        success = await es.ping()
        if success:
            break
        await asyncio.sleep(1)
        print('waiting ES ping...')

    if not success:
        raise SystemExit('ES ping failed!')

    # ignore 400 cause by IndexAlreadyExistsException when creating an index
    await es.indices.create(index=ES_ITEMS_INDEX, ignore=400)


@app.on_event("shutdown")
async def app_shutdown():
    await es.close()
    client.close()


class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None


@app.get('/')
async def read_root():
    return {'Hello': 'world!'}


@app.post('/items')
async def create_item(item: Item):
    item = item.dict()

    inserted_item = await db.item.insert_one(item)
    item['_id'] = inserted_item.inserted_id
    _adapt_id_to_ui(item)

    await es.create(
        index=ES_ITEMS_INDEX,
        doc_type='item',
        id=item['id'],
        body=item,
    )

    return item


@app.get('/items/{item_id}')
async def read_item(item_id: str):
    try:
        bson_id = ObjectId(item_id)
    except bson.errors.InvalidId:
        raise HTTPException(422)

    doc = await db.item.find_one({'_id': bson_id})
    if doc is None:
        raise HTTPException(404)

    _adapt_id_to_ui(doc)
    return doc


@app.delete('/items/{item_id}')
async def delete_item(item_id: str):
    await db.item.delete_many({'_id': ObjectId(item_id)})


@app.get('/items')
async def read_items(limit: Optional[int] = None):
    items = await db.item.find().to_list(length=limit)
    for item in items:
        _adapt_id_to_ui(item)
    return items


@app.get('/search')
async def read_items(q: str):
    res = await es.search(
        index=ES_ITEMS_INDEX,
        doc_type='item',
        body={"query": {"match": {"description": q}}}
    )
    items = [doc['_source'] for doc in res['hits']['hits']]
    return items


def _adapt_id_to_ui(item):
    item['id'] = str(item.pop('_id'))
