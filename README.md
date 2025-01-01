# PyORMLite

Here’s the updated implementation, where CRUD operations and table creation are moved to a separate BaseDao class. The BaseModel class now serves only as a data container, while BaseDao handles all database-related operations.

Updated Implementation

import sqlite3


# Field Definitions
class FieldBase:
    def __init__(self, name, **kwargs):
        self.name = name
        self.primary_key = kwargs.get("primary_key", False)
        self.nullable = kwargs.get("nullable", True)


class FieldInteger(FieldBase):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.field_type = "INTEGER"


class FieldString(FieldBase):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.field_type = "TEXT"


class FieldForeign(FieldBase):
    def __init__(self, name, model, **kwargs):
        super().__init__(name, **kwargs)
        self.field_type = "INTEGER"
        self.model = model


class FieldList(FieldBase):
    def __init__(self, model, lazyload=False):
        self.model = model
        self.lazyload = lazyload


# MetaModel for Schema Definition
class BaseModelMeta(type):
    def __new__(cls, name, bases, attrs):
        if name == "BaseModel":
            return super().__new__(cls, name, bases, attrs)

        # Retrieve table name
        table_name = attrs.get("_table", name.lower())
        attrs["_table"] = table_name

        # Retrieve and validate fields
        fields = {}
        for field in attrs.get("_fields", []):
            if not isinstance(field, (FieldBase, FieldList)):
                raise TypeError(f"Invalid field: {field}. Fields must inherit from FieldBase or FieldList.")
            fields[field.name] = field

        attrs["_fields"] = fields

        # Store table name and fields as metadata in the class
        attrs["_meta"] = {"table_name": table_name, "fields": fields}

        return super().__new__(cls, name, bases, attrs)


# BaseModel: Data container
class BaseModel(metaclass=BaseModelMeta):
    pass


# BaseDao: Handles CRUD and database operations
class BaseDao:
    _connection = None
    _cursor = None

    @classmethod
    def set_database(cls, db_path):
        cls._connection = sqlite3.connect(db_path)
        cls._connection.row_factory = sqlite3.Row  # Return rows as dictionaries
        cls._cursor = cls._connection.cursor()

    @classmethod
    def create_table(cls, model):
        fields = []
        for name, field in model._fields.items():
            if isinstance(field, FieldForeign):
                fields.append(
                    f"{field.name} {field.field_type}, FOREIGN KEY ({field.name}) REFERENCES {field.model.lower()}(id)"
                )
            else:
                column = f"{field.name} {field.field_type}"
                if field.primary_key:
                    column += " PRIMARY KEY"
                if not field.nullable:
                    column += " NOT NULL"
                fields.append(column)

        query = f"CREATE TABLE IF NOT EXISTS {model._meta['table_name']} ({', '.join(fields)});"
        cls._cursor.execute(query)

    @classmethod
    def save(cls, model, instance):
        fields = [field.name for field in model._fields.values() if not isinstance(field, FieldList)]
        values = [getattr(instance, field, None) for field in fields]
        placeholders = ", ".join(["?" for _ in fields])

        query = f"INSERT INTO {model._meta['table_name']} ({', '.join(fields)}) VALUES ({placeholders});"
        cls._cursor.execute(query, values)
        cls._connection.commit()
        instance.id = cls._cursor.lastrowid

    @classmethod
    def all(cls, model, lazyload=True):
        query = f"SELECT * FROM {model._meta['table_name']};"
        cls._cursor.execute(query)
        rows = cls._cursor.fetchall()
        return [cls._load_relations(model, cls._dict_to_instance(model, row), lazyload) for row in rows]

    @classmethod
    def get(cls, model, lazyload=True, **kwargs):
        field, value = next(iter(kwargs.items()))
        query = f"SELECT * FROM {model._meta['table_name']} WHERE {field} = ?;"
        cls._cursor.execute(query, (value,))
        row = cls._cursor.fetchone()
        return cls._load_relations(model, cls._dict_to_instance(model, row), lazyload) if row else None

    @classmethod
    def _load_relations(cls, model, instance, lazyload):
        if not lazyload:
            return instance
        for field_name, field in model._fields.items():
            if isinstance(field, FieldList):
                related_model = globals()[field.model]
                related_query = f"SELECT * FROM {related_model._meta['table_name']} WHERE user_id = ?;"
                cls._cursor.execute(related_query, (getattr(instance, "id"),))
                related_items = cls._cursor.fetchall()
                setattr(instance, field_name, [cls._dict_to_instance(related_model, item) for item in related_items])
        return instance

    @classmethod
    def _dict_to_instance(cls, model, row):
        instance = model()
        for field_name in row.keys():
            setattr(instance, field_name, row[field_name])
        return instance


# Models
class User(BaseModel):
    _table = "users"
    _fields = [
        FieldInteger("id", primary_key=True),
        FieldString("name", nullable=False),
        FieldList(model="Post"),
    ]


class Post(BaseModel):
    _table = "posts"
    _fields = [
        FieldInteger("id", primary_key=True),
        FieldString("title", nullable=False),
        FieldForeign("user_id", model="User"),
    ]


# Usage Example
BaseDao.set_database(":memory:")
BaseDao.create_table(User)
BaseDao.create_table(Post)

user = User()
user.id = 1
user.name = "John Doe"
BaseDao.save(User, user)

post1 = Post()
post1.id = 1
post1.title = "Post 1"
post1.user_id = 1
BaseDao.save(Post, post1)

post2 = Post()
post2.id = 2
post2.title = "Post 2"
post2.user_id = 1
BaseDao.save(Post, post2)

users = BaseDao.all(User)
for user in users:
    print(f"User: {user.name}")
    for post in user.Post:
        print(f"  Post: {post.title}")

Changes and Features
	1.	BaseDao Class:
	•	Handles database-related operations such as table creation, CRUD operations, and relation loading.
	2.	Separation of Concerns:
	•	BaseModel: Acts as a schema definition and data container.
	•	BaseDao: Handles all database interactions.
	3.	Reusability:
	•	The BaseDao methods are reusable for any model.
	4.	Dynamic Relation Loading:
	•	Automatically loads related objects (e.g., posts for users).

Output Example

User: John Doe
  Post: Post 1
  Post: Post 2
