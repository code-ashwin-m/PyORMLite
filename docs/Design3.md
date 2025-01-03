Below is the complete code for a lightweight ORM with advanced query-building capabilities (QueryBuilder, DeleteBuilder, UpdateBuilder), allowing users to build and execute complex queries using methods like equal, not_equal, greater_than, less_than, in_, and not_in.

Complete Code

Field Definitions

These define the schema of each model.
```python
class FieldBase:
    def __init__(self, name, field_type, nullable=True, primary_key=False):
        self.name = name
        self.field_type = field_type
        self.nullable = nullable
        self.primary_key = primary_key


class FieldInteger(FieldBase):
    def __init__(self, name, nullable=True, primary_key=False):
        super().__init__(name, "INTEGER", nullable, primary_key)


class FieldString(FieldBase):
    def __init__(self, name, nullable=True):
        super().__init__(name, "TEXT", nullable)


class FieldForeign(FieldBase):
    def __init__(self, name, model, nullable=True):
        super().__init__(name, "INTEGER", nullable)
        self.model = model


class FieldList:
    def __init__(self, model, lazyload=True):
        self.model = model
        self.lazyload = lazyload
```

Model Base Class

Used to define models (e.g., User, Post).
```python
class BaseModel:
    _table = None
    _fields = []

    @classmethod
    def _meta(cls):
        return {
            "table_name": cls._table,
            "fields": {field.name: field for field in cls._fields},
        }
```
Query Builders

These builders provide chainable methods for constructing SELECT, DELETE, and UPDATE SQL queries.
```python
class QueryBuilder:
    def __init__(self, table):
        self.table = table
        self.conditions = []
        self.fields = "*"

    def select(self, *fields):
        self.fields = ", ".join(fields) if fields else "*"
        return self

    def equal(self, field, value):
        self.conditions.append((field, "=", value))
        return self

    def not_equal(self, field, value):
        self.conditions.append((field, "!=", value))
        return self

    def greater_than(self, field, value):
        self.conditions.append((field, ">", value))
        return self

    def less_than(self, field, value):
        self.conditions.append((field, "<", value))
        return self

    def in_(self, field, values):
        placeholders = ", ".join("?" for _ in values)
        self.conditions.append((field, f"IN ({placeholders})", values))
        return self

    def not_in(self, field, values):
        placeholders = ", ".join("?" for _ in values)
        self.conditions.append((field, f"NOT IN ({placeholders})", values))
        return self

    def build(self):
        where_clause = ""
        params = []

        if self.conditions:
            clauses = []
            for field, operator, value in self.conditions:
                clauses.append(f"{field} {operator}")
                if isinstance(value, list):
                    params.extend(value)
                else:
                    params.append(value)
            where_clause = " WHERE " + " AND ".join(clauses)

        query = f"SELECT {self.fields} FROM {self.table}{where_clause};"
        return query, params


class DeleteBuilder:
    def __init__(self, table):
        self.table = table
        self.conditions = []

    def equal(self, field, value):
        self.conditions.append((field, "=", value))
        return self

    def not_equal(self, field, value):
        self.conditions.append((field, "!=", value))
        return self

    def greater_than(self, field, value):
        self.conditions.append((field, ">", value))
        return self

    def less_than(self, field, value):
        self.conditions.append((field, "<", value))
        return self

    def in_(self, field, values):
        placeholders = ", ".join("?" for _ in values)
        self.conditions.append((field, f"IN ({placeholders})", values))
        return self

    def not_in(self, field, values):
        placeholders = ", ".join("?" for _ in values)
        self.conditions.append((field, f"NOT IN ({placeholders})", values))
        return self

    def build(self):
        if not self.conditions:
            raise ValueError("DELETE queries require at least one condition.")

        where_clause = ""
        params = []

        clauses = []
        for field, operator, value in self.conditions:
            clauses.append(f"{field} {operator}")
            if isinstance(value, list):
                params.extend(value)
            else:
                params.append(value)
        where_clause = " WHERE " + " AND ".join(clauses)

        query = f"DELETE FROM {self.table}{where_clause};"
        return query, params


class UpdateBuilder:
    def __init__(self, table):
        self.table = table
        self.updates = {}
        self.conditions = []

    def set(self, **kwargs):
        self.updates.update(kwargs)
        return self

    def equal(self, field, value):
        self.conditions.append((field, "=", value))
        return self

    def not_equal(self, field, value):
        self.conditions.append((field, "!=", value))
        return self

    def greater_than(self, field, value):
        self.conditions.append((field, ">", value))
        return self

    def less_than(self, field, value):
        self.conditions.append((field, "<", value))
        return self

    def in_(self, field, values):
        placeholders = ", ".join("?" for _ in values)
        self.conditions.append((field, f"IN ({placeholders})", values))
        return self

    def not_in(self, field, values):
        placeholders = ", ".join("?" for _ in values)
        self.conditions.append((field, f"NOT IN ({placeholders})", values))
        return self

    def build(self):
        if not self.updates:
            raise ValueError("UPDATE queries require at least one field to update.")

        set_clause = ", ".join([f"{key} = ?" for key in self.updates.keys()])
        where_clause = ""
        params = list(self.updates.values())

        if self.conditions:
            clauses = []
            for field, operator, value in self.conditions:
                clauses.append(f"{field} {operator}")
                if isinstance(value, list):
                    params.extend(value)
                else:
                    params.append(value)
            where_clause = " WHERE " + " AND ".join(clauses)

        query = f"UPDATE {self.table} SET {set_clause}{where_clause};"
        return query, params
```
BaseDao

Handles database operations and exposes builders to the user.
```python
class BaseDao:
    _connection = None
    _cursor = None

    @classmethod
    def set_database(cls, db_path):
        cls._connection = sqlite3.connect(db_path)
        cls._connection.row_factory = sqlite3.Row
        cls._cursor = cls._connection.cursor()

    @classmethod
    def create_table(cls, model):
        fields = []
        for field in model._fields:
            column = f"{field.name} {field.field_type}"
            if field.primary_key:
                column += " PRIMARY KEY"
            if not field.nullable:
                column += " NOT NULL"
            fields.append(column)

        query = f"CREATE TABLE IF NOT EXISTS {model._table} ({', '.join(fields)});"
        cls._cursor.execute(query)

    @classmethod
    def execute_query(cls, query, params=()):
        cls._cursor.execute(query, params)
        cls._connection.commit()
        return cls._cursor.fetchall()

    @classmethod
    def query_builder(cls, model):
        return QueryBuilder(model._table)

    @classmethod
    def delete_builder(cls, model):
        return DeleteBuilder(model._table)

    @classmethod
    def update_builder(cls, model):
        return UpdateBuilder(model._table)
```
Usage
```python
class User(BaseModel):
    _table = "users"
    _fields = [
        FieldInteger("id", primary_key=True),
        FieldString("name", nullable=False),
        FieldString("email", nullable=True),
    ]

BaseDao.set_database(":memory:")
BaseDao.create_table(User)

# Insert a user
BaseDao.execute_query("INSERT INTO users (name, email) VALUES (?, ?)", ["John Doe", "john@example.com"])

# Query users
query, params = BaseDao.query_builder(User).equal("name", "John Doe").build()
print(BaseDao.execute_query(query, params))
```
Explanation
	1.	Models: Define schema using BaseModel and fields.
	2.	Builders: Use chainable methods to construct complex queries.
	3.	BaseDao: Exposes query builders and handles execution.
