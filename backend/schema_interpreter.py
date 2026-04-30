from backend.db import engine
from sqlalchemy import text
from backend.logger import setup_logger

logger = setup_logger(__name__)

def interpret_and_create_tables(db_config: dict):
    """
    Parses the db_config (dict format of config.db) and creates tables in the database.
    """
    tables = db_config.get("tables", [])
    
    type_mapping = {
        "string": "TEXT",
        "number": "INTEGER",
        "boolean": "BOOLEAN",
        "date": "TEXT" # SQLite fallback
    }
    
    with engine.connect() as conn:
        for table in tables:
            table_name = table.get("name")
            if not table_name:
                continue
                
            fields = table.get("fields", [])
            
            columns_sql = []
            foreign_keys_sql = []
            
            # Auto-inject app_id isolation column
            columns_sql.append("app_id TEXT NOT NULL")
            
            for field in fields:
                col_name = field.get("name")
                if not col_name:
                    continue
                    
                col_type = type_mapping.get(field.get("type", "string"), "TEXT")
                
                mods = []
                if field.get("is_primary"):
                    mods.append("PRIMARY KEY")
                elif field.get("required"):
                    mods.append("NOT NULL")
                    
                columns_sql.append(f"{col_name} {col_type} {' '.join(mods)}".strip())
                
                # Handle foreign keys
                fk = field.get("foreign_key")
                if fk and "." in fk:
                    try:
                        ref_table, ref_field = fk.split(".")
                        foreign_keys_sql.append(f"FOREIGN KEY({col_name}) REFERENCES {ref_table}({ref_field})")
                    except Exception as e:
                        logger.warning(f"Invalid foreign key format '{fk}': {e}")
            
            if not columns_sql:
                continue
                
            all_defs = columns_sql + foreign_keys_sql
            create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n  {',\n  '.join(all_defs)}\n);"
            
            logger.info(f"Executing SQL Schema:\n{create_sql}")
            try:
                conn.execute(text(create_sql))
                conn.commit()
                logger.info(f"Table '{table_name}' dynamically created or verified.")
            except Exception as e:
                logger.error(f"Error executing schema for {table_name}: {e}")
