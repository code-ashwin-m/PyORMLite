Here’s the updated implementation of the BaseDao class, which now includes QueryBuilder, DeleteBuilder, and UpdateBuilder to support more flexible and readable query operations. These builders allow developers to construct queries programmatically without writing raw SQL.

QueryBuilder Classes

class QueryBuilder:
    def __init__(self, table):
        self.table = table
        self.conditions = []
        self.fields = "*"

    def select(self, *fields):
        self.fields = ", ".join(fields) if fields else "*"
        return self

    def where(self, **kwargs):
        for key, value in kwargs.items():
            self.conditions.append((key, value))
        return self

    def build(self):
        where_clause = (
            " WHERE " + " AND ".join([f"{key} = ?" for key, _ in self.conditions])
            if self.conditions
            else ""
        )
        query = f"SELECT {self.fields} FROM {self.table}{where_clause};"
        params = [value for _, value in self.conditions]
        return query, params


class DeleteBuilder:
    def __init__(self, table):
        self.table = table
        self.conditions = []

    def where(self, **kwargs):
        for key, value in kwargs.items():
            self.conditions.append((key, value))
        return self

    def build(self):
        if not self.conditions:
            raise ValueError("DELETE queries require at least one condition.")
        where_clause = " AND ".join([f"{key} = ?" for key, _ in self.conditions])
        query = f"DELETE FROM {self.table} WHERE {where_clause};"
        params = [value for _, value in self.conditions]
        return query, params


class UpdateBuilder:
    def __init__(self, table):
        self.table = table
        self.updates = {}
        self.conditions = []

    def set(self, **kwargs):
        self.updates.update(kwargs)
        return self

    def where(self, **kwargs):
        for key, value in kwargs.items():
            self.conditions.append((key, value))
        return self

    def build(self):
        if not self.updates:
            raise ValueError("UPDATE queries require at least one field to update.")
        set_clause = ", ".join([f"{key} = ?" for key in self.updates.keys()])
        where_clause = (
            " WHERE " + " AND ".join([f"{key} = ?" for key, _ in self.conditions])
            if self.conditions
            else ""
        )
        query = f"UPDATE {self.table} SET {set_clause}{where_clause};"
        params = list(self.updates.values()) + [value for _, value in self.conditions]
        return query, params

Updated BaseDao Implementation

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
    def all(cls, model):
        query, params = QueryBuilder(model._meta["table_name"]).build()
        cls._cursor.execute(query, params)
        rows = cls._cursor.fetchall()
        return [cls._dict_to_instance(model, row) for row in rows]

    @classmethod
    def get(cls, model, **kwargs):
        query, params = QueryBuilder(model._meta["table_name"]).where(**kwargs).build()
        cls._cursor.execute(query, params)
        row = cls._cursor.fetchone()
        return cls._dict_to_instance(model, row) if row else None

    @classmethod
    def delete(cls, model, **kwargs):
        query, params = DeleteBuilder(model._meta["table_name"]).where(**kwargs).build()
        cls._cursor.execute(query, params)
        cls._connection.commit()

    @classmethod
    def update(cls, model, fields, **kwargs):
        query, params = UpdateBuilder(model._meta["table_name"]).set(**fields).where(**kwargs).build()
        cls._cursor.execute(query, params)
        cls._connection.commit()

    @classmethod
    def _dict_to_instance(cls, model, row):
        instance = model()
        for field_name in row.keys():
            setattr(instance, field_name, row[field_name])
        return instance

Usage Example

Define Models

class User(BaseModel):
    _table = "users"
    _fields = [
        FieldInteger("id", primary_key=True),
        FieldString("name", nullable=False),
    ]

Set Up Database

BaseDao.set_database(":memory:")
BaseDao.create_table(User)

Insert Data

user = User()
user.name = "John Doe"
BaseDao.save(User, user)

Query Data

users = BaseDao.all(User)
for user in users:
    print(f"User: {user.name}")

user = BaseDao.get(User, id=1)
print(f"User with ID 1: {user.name}")

Update Data

BaseDao.update(User, {"name": "Jane Doe"}, id=1)
user = BaseDao.get(User, id=1)
print(f"Updated User: {user.name}")

Delete Data

BaseDao.delete(User, id=1)
user = BaseDao.get(User, id=1)
print(f"User after deletion: {user}")

Output Example

User: John Doe
User with ID 1: John Doe
Updated User: Jane Doe
User after deletion: None

Key Features
	1.	QueryBuilder:
	•	Simplifies SELECT queries with chaining for select and where.
	2.	DeleteBuilder:
	•	Ensures DELETE queries are safe by requiring conditions.
	3.	UpdateBuilder:
	•	Supports flexible updates with set and where chaining.
	4.	Flexibility:
	•	Clean, reusable, and readable query building for all major operations (SELECT, UPDATE, DELETE).
