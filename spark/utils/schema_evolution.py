# PySpark Additive Schema Evolution Guard
from pyspark.sql.types import StructType

def validate_additive_schema(current_schema: StructType, incoming_schema: StructType) -> bool:
    current_fields = {f.name for f in current_schema.fields}
    incoming_fields = {f.name for f in incoming_schema.fields}
    return current_fields.issubset(incoming_fields)
