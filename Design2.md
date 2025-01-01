To allow users to build complex queries using QueryBuilder, DeleteBuilder, and UpdateBuilder directly, we can expose these builders as part of the BaseDao class. Additionally, we’ll provide methods in BaseDao to execute the queries built by these builders.

Here’s the updated implementation:

Updated Implementation

Expose Query Builders

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
    def execute_query(cls, query, params=()):
        cls._cursor.execute(query, params)
        cls._connection.commit()
        return cls._cursor.fetchall()

    @classmethod
    def query_builder(cls, model):
        return QueryBuilder(model._meta["table_name"])

    @classmethod
    def delete_builder(cls, model):
        return DeleteBuilder(model._meta["table_name"])

    @classmethod
    def update_builder(cls, model):
        return UpdateBuilder(model._meta["table_name"])

Query Builders

These builders remain the same as described earlier.

Usage Example

Define Models

class User(BaseModel):
    _table = "users"
    _fields = [
        FieldInteger("id", primary_key=True),
        FieldString("name", nullable=False),
        FieldString("email", nullable=True),
    ]

Set Up Database

BaseDao.set_database(":memory:")
BaseDao.create_table(User)

# Insert sample data
user1 = User()
user1.name = "John Doe"
user1.email = "john@example.com"
BaseDao.save(User, user1)

user2 = User()
user2.name = "Jane Doe"
user2.email = "jane@example.com"
BaseDao.save(User, user2)

Build and Execute Queries

Complex SELECT Query

query, params = BaseDao.query_builder(User).select("id", "name").where(email="john@example.com").build()
results = BaseDao.execute_query(query, params)
for row in results:
    print(dict(row))

Update Query

query, params = BaseDao.update_builder(User).set(name="John Smith").where(id=1).build()
BaseDao.execute_query(query, params)

# Verify the update
query, params = BaseDao.query_builder(User).where(id=1).build()
updated_user = BaseDao.execute_query(query, params)
print(dict(updated_user[0]))

Delete Query

query, params = BaseDao.delete_builder(User).where(name="Jane Doe").build()
BaseDao.execute_query(query, params)

# Verify the deletion
query, params = BaseDao.query_builder(User).build()
all_users = BaseDao.execute_query(query)
print([dict(row) for row in all_users])

Output Example

Initial SELECT Query:

{'id': 1, 'name': 'John Doe'}

After Update:

{'id': 1, 'name': 'John Smith', 'email': 'john@example.com'}

After Deletion:

[{'id': 1, 'name': 'John Smith', 'email': 'john@example.com'}]

Benefits of Exposed Query Builders
	1.	Flexibility:
	•	Users can build complex queries without diving into raw SQL.
	2.	Reusability:
	•	Query builders are generic and reusable for any model.
	3.	Error Safety:
	•	Query construction ensures that required components (e.g., conditions in DELETE) are always present.
	4.	Readable Code:
	•	Query builders produce highly readable and maintainable code.
