from typing import List, Type, Optional
import sqlite3, importlib

class BaseBuilder:
    def __init__(self):
        self.conditions = []
        self.current_logical_operator = None
        self.query = None
        self.params = []

    def _add_condition(self, field, operator, value):
        if self.conditions:
            self.conditions.append((self.current_logical_operator, (field, operator, value)))
        else:
            self.conditions.append((None, (field, operator, value)))
        return self

    def _and(self):
        self.current_logical_operator = "AND"
        return self
    
    def _or(self):
        self.current_logical_operator = "OR"
        return self
    
    def _eq(self, field, value):
        return self._add_condition(field, "= ?", value)

    def _not_eq(self, field, value):
        return self._add_condition(field, "!= ?", value)
    
    def _lt(self, field, value):
        return self._add_condition(field, "< ?", value)

    def _gt(self, field, value):
        return self._add_condition(field, "> ?", value)
    
    def _le(self, field, value):
        return self._add_condition(field, "<= ?", value)

    def _ge(self, field, value):
        return self._add_condition(field, ">= ?", value)
    
    def _in(self, field, values):
        if isinstance(values, QueryBuilder):
            placeholder = values.query
            values = None
        else:
            placeholder = ", ".join("?" for _ in values)
        return self._add_condition(field, f"IN ({placeholder})", values)
    
    def _not_in(self, field, values):
        if isinstance(values, QueryBuilder):
            placeholder = values.query
            values = None
        else:
            placeholder = ", ".join("?" for _ in values)
        return self._add_condition(field, f"NOT IN ({placeholder})", values)
    
    def build_conditions(self):
        clauses = []
        params = []
        for logical_operator, (field, operator, value) in self.conditions:
            if logical_operator:
                clauses.append(f'{logical_operator} {field} {operator}')
            else:
                clauses.append(f'{field} {operator}')
            
            if value:
                if isinstance(value, list):
                    params.extend(value)
                else:
                    params.append(value)
        return " ".join(clauses), params
        
class QueryBuilder(BaseBuilder):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.fields = "*"

    def select(self, *fields):
        self.fields = ", ".join(fields) if fields else "*"
        return self

    def where(self, **kwargs):
        for key, value in kwargs.items():
            self.conditions.append((None, (key, "= ?", value)))
        return self

    def build(self):
        where_clause, params = self.build_conditions()
        query = f"SELECT {self.fields} FROM {self.model._table}"
        if where_clause:
            query += f" WHERE {where_clause}"
        self.query = query
        self.params = params
        return self

class UpdateBuilder(BaseBuilder):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.updates = {}

    def set(self, **kwargs):
        self.updates.update(kwargs)
        return self

    def where(self, **kwargs):
        for key, value in kwargs.items():
            self.conditions.append((None, (key, "= ?", value)))
        return self

    def build(self):
        if not self.updates:
            raise ValueError("UPDATE queries require at least one field to update.")
        set_clause = ", ".join([f"{key} = ?" for key in self.updates.keys()])

        where_clause, params = self.build_conditions()
        if where_clause:
            where_clause = f" WHERE {where_clause}"

        self.query = f"UPDATE {self.model._table} SET {set_clause}{where_clause}"
        self.params = list(self.updates.values()) + params
        return self
    
class DeleteBuilder(BaseBuilder):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def where(self, **kwargs):
        for key, value in kwargs.items():
            self.conditions.append((None, (key, "= ?", value)))
        return self

    def build(self):
        if not self.conditions:
            raise ValueError("DELETE queries require at least one condition.")
        # where_clause = " AND ".join([f"{key} = ?" for key, _ in self.conditions])
        where_clause, params = self.build_conditions()
        self.query = f"DELETE FROM {self.model._table} WHERE {where_clause};"
        self.params = params
        return self


    
class BaseMeta(type):
    """Metaclass to create table from class and map columns."""
    def __new__(cls, name, bases, dct):
        if name == "DaoMeta":
            return super().__new__(cls, name, bases, dct)
        
        # Retrieve table name
        table_name = dct.get("_table", name)
        dct["_table"] = table_name

        # Retrieve and validate fields
        fields = []
        for field in dct.get("_fields", []):
            if not isinstance(field, (BaseField, FieldList)):
                raise TypeError(f"Invalid field: {field}. Fields must inherit from FieldBase or FieldList.")
            fields.append(field)

        dct["_fields"] = fields
        # Store table name and fields as metadata in the class
        dct["_meta"] = {"table_name": table_name, "fields": fields}

        return super().__new__(cls, name, bases, dct)

# BaseModel: Data container
class BaseModel(metaclass=BaseMeta):
    pass

# BaseDao: Handles CRUD and database operations
class BaseDao:
    _connection = None
    _cursor = None
    _module = None

    @classmethod
    def set_database(cls, db_path):
        cls._connection = sqlite3.connect(db_path)
        cls._connection.row_factory = sqlite3.Row  # Return rows as dictionaries
        cls._cursor = cls._connection.cursor()
    
    @classmethod
    def set_module(cls, module_name: str):
        # Dynamically import the module
        cls._module = importlib.import_module(module_name)

    @classmethod
    def create_table(cls, model):
        fields = []
        foreign = []
        primary_key = []
        for field in model._fields:
            if isinstance(field, FieldForeign):
                foreign.append(
                    f"FOREIGN KEY ({field.name}) REFERENCES {field.model}(id)"
                )
                fields.append(
                    f"{field.name} {field.type}"
                )
            elif isinstance(field, FieldList):
                pass
            else:
                column = f"{field.name} {field.type}"
                if field.generated_id:
                    primary_key.append(
                        f"PRIMARY KEY({field.name} AUTOINCREMENT)"
                    )
                if not field.nullable:
                    column += " NOT NULL"
                if field.unique:
                    column += " UNIQUE"

                fields.append(column)
        
        fields.extend(primary_key)
        fields.extend(foreign)
        query = f"CREATE TABLE IF NOT EXISTS {model._meta['table_name']} ({', '.join(fields)});"
        cls._cursor.execute(query)

    @classmethod
    def save(cls, model, instance):
        fields = [field.name for field in model._fields if not isinstance(field, FieldList)]
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
    def get_by_id(cls, model, id: int, lazyload=True):
        query = f"SELECT * FROM {model._meta['table_name']} WHERE id = ?;"
        cls._cursor.execute(query, (id,))
        row = cls._cursor.fetchone()
        return cls._load_relations(model, cls._dict_to_instance(model, row), lazyload) if row else None
    
    @classmethod
    def _load_relations(cls, model, instance, lazyload):
        if not lazyload:
            return instance
        for field in model._fields:
            if isinstance(field, FieldList):
                related_model = getattr(cls._module, field.model)
                foriegn_name = [field1.name for field1 in related_model._fields if isinstance(field1, FieldForeign) and field1.model == model.__name__]
                related_query = f"SELECT * FROM {related_model._meta['table_name']} WHERE {foriegn_name[0]} = ?;"
                cls._cursor.execute(related_query, (getattr(instance, "id"),))
                related_items = cls._cursor.fetchall()
                setattr(instance, field.name, [cls._dict_to_instance(related_model, item) for item in related_items])
        return instance

    @classmethod
    def _dict_to_instance(cls, model, row):
        instance = model()
        for field_name in row.keys():
            setattr(instance, field_name, row[field_name])
        return instance

    @classmethod
    def execute_query(cls, query_builder, lazyload = True):
        cls._cursor.execute(query_builder.query, query_builder.params)
        cls._connection.commit()
        rows = cls._cursor.fetchall()
        # print([dict(row) for row in rows])
        return [cls._load_relations(query_builder.model, cls._dict_to_instance(query_builder.model, row), lazyload) for row in rows]
    
    @classmethod
    def query_builder(cls, model):
        return QueryBuilder(model)
    
    @classmethod
    def delete_builder(cls, model):
        return DeleteBuilder(model)

    @classmethod
    def update_builder(cls, model):
        return UpdateBuilder(model)
    
class BaseField:
    """Base class for fields in the model."""
    def __init__(self, name: str, 
                 default_value: Optional[str] = None, 
                 generated_id: Optional[str] = False,
                 nullable: Optional[str] = True,
                 unique: Optional[str] = False
                 ):
        self.name = name
        self.default_value = default_value
        self.generated_id = generated_id
        self.nullable = nullable
        self.unique = unique

    def to_db_value(self, value):
        return value

class FieldForeign(BaseField):
    type = "INTEGER"
    """Represents a foreign key to another table."""
    def __init__(self, column_name: str, model:str):
        super().__init__(column_name)
        self.model = model

class FieldInteger(BaseField):
    type = "INTEGER"
    
class FieldString(BaseField):
    type = "TEXT"

class FieldList(BaseField):
    def __init__(self, name: str, model: str, lazyload=False):
        self.name = name
        self.model = model
        self.lazyload = lazyload
    
