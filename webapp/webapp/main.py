import os
from typing import Optional

import bson.errors
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI, Depends
from fastapi.exceptions import HTTPException
from pydantic import BaseModel

MONGODB_ADDRESS = os.getenv('MONGODB_ADDRESS', 'mongodb://localhost:27017')

app = FastAPI()


class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None


async def get_db():
    client = AsyncIOMotorClient(MONGODB_ADDRESS)
    db = client.test
    try:
        yield db
    finally:
        client.close()


@app.get('/')
async def read_root():
    return {'Hello': 'world!'}


@app.post('/items')
async def create_item(item: Item, db=Depends(get_db)):
    item = item.dict()
    inserted_item = await db.item.insert_one(item)
    item['_id'] = inserted_item.inserted_id
    _adapt_id_to_ui(item)
    return item


@app.get('/items/{item_id}')
async def read_item(item_id: str, db=Depends(get_db)):
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
async def delete_item(item_id: str, db=Depends(get_db)):
    await db.item.delete_many({'_id': ObjectId(item_id)})


@app.get('/items')
async def read_items(db=Depends(get_db), limit: Optional[int] = None):
    items = await db.item.find().to_list(length=limit)
    for item in items:
        _adapt_id_to_ui(item)
    return items


def _adapt_id_to_ui(item):
    item['id'] = str(item.pop('_id'))
