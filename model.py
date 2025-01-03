from ormlite.model import BaseModel, FieldInteger, FieldString, FieldForeign, FieldList
from typing import List
class Post(BaseModel):
    _table = "Posts"
    _fields = [
        FieldInteger('id', generated_id=True),
        FieldString('title', unique=True),
        FieldForeign('user_id', 'User'),
        FieldList('tagst', 'Tag', lazyload=False)
    ]
    
class Tag(BaseModel):
    _table = "Tags"
    _fields = [
        FieldInteger('id', generated_id=True),
        FieldString('name'),
        FieldForeign('post_id', 'Post')
    ]


class User(BaseModel):
    _table = "Users"
    _fields = [
        FieldInteger('id', generated_id=True),
        FieldString('name', nullable=False, default_value="Hai", unique=True),
        FieldList('posts', 'Post', lazyload=False)
    ]

    id: int = None
    name: str = None
    posts: List[Post] = []



    
    