"""
SQL domain templates for NLP2CMD.

Contains all SQL-related command templates.
"""

SQL_TEMPLATES = {
    'select': "SELECT {columns} FROM {table}{where}{order}{limit};",
    'select_all': "SELECT * FROM {table}{where}{order}{limit};",
    'select_distinct': "SELECT DISTINCT {columns} FROM {table}{where}{order}{limit};",
    'insert': "INSERT INTO {table} ({columns}) VALUES ({values});",
    'insert_multiple': "INSERT INTO {table} ({columns}) VALUES {values};",
    'update': "UPDATE {table} SET {set_clause}{where};",
    'delete': "DELETE FROM {table}{where};",
    'truncate': "TRUNCATE TABLE {table};",
    'aggregate': "SELECT {aggregations} FROM {table}{where}{group}{order};",
    'count': "SELECT COUNT(*) FROM {table}{where};",
    'count_distinct': "SELECT COUNT(DISTINCT {column}) FROM {table}{where};",
    'sum': "SELECT SUM({column}) FROM {table}{where};",
    'avg': "SELECT AVG({column}) FROM {table}{where};",
    'min_max': "SELECT MIN({column}), MAX({column}) FROM {table}{where};",
    # Joins
    'join': "SELECT {columns} FROM {table1} {join_type} JOIN {table2} ON {condition}{where}{order}{limit};",
    'inner_join': "SELECT {columns} FROM {table1} INNER JOIN {table2} ON {table1}.{key1} = {table2}.{key2}{where};",
    'left_join': "SELECT {columns} FROM {table1} LEFT JOIN {table2} ON {table1}.{key1} = {table2}.{key2}{where};",
    'right_join': "SELECT {columns} FROM {table1} RIGHT JOIN {table2} ON {table1}.{key1} = {table2}.{key2}{where};",
    'full_join': "SELECT {columns} FROM {table1} FULL OUTER JOIN {table2} ON {table1}.{key1} = {table2}.{key2}{where};",
    # Subqueries
    'subquery_in': "SELECT {columns} FROM {table} WHERE {column} IN (SELECT {subcolumn} FROM {subtable}{subwhere});",
    'subquery_exists': "SELECT {columns} FROM {table} WHERE EXISTS (SELECT 1 FROM {subtable} WHERE {condition});",
    # DDL
    'create_table': "CREATE TABLE {table} ({columns});",
    'create_table_if_not_exists': "CREATE TABLE IF NOT EXISTS {table} ({columns});",
    'drop_table': "DROP TABLE {table};",
    'drop_table_if_exists': "DROP TABLE IF EXISTS {table};",
    'alter_add_column': "ALTER TABLE {table} ADD COLUMN {column} {datatype};",
    'alter_drop_column': "ALTER TABLE {table} DROP COLUMN {column};",
    'alter_rename_column': "ALTER TABLE {table} RENAME COLUMN {old_name} TO {new_name};",
    'alter_modify_column': "ALTER TABLE {table} MODIFY COLUMN {column} {datatype};",
    # Indexes
    'create_index': "CREATE INDEX {index_name} ON {table} ({columns});",
    'create_unique_index': "CREATE UNIQUE INDEX {index_name} ON {table} ({columns});",
    'drop_index': "DROP INDEX {index_name};",
    # Views
    'create_view': "CREATE VIEW {view_name} AS SELECT {columns} FROM {table}{where};",
    'drop_view': "DROP VIEW {view_name};",
    # Window functions
    'window_row_number': "SELECT {columns}, ROW_NUMBER() OVER ({partition} ORDER BY {order_column}) AS row_num FROM {table};",
    'window_rank': "SELECT {columns}, RANK() OVER ({partition} ORDER BY {order_column}) AS rank FROM {table};",
    'window_lag': "SELECT {columns}, LAG({column}, {offset}) OVER ({partition} ORDER BY {order_column}) AS prev_val FROM {table};",
    'window_lead': "SELECT {columns}, LEAD({column}, {offset}) OVER ({partition} ORDER BY {order_column}) AS next_val FROM {table};",
    # CTEs
    'cte': "WITH {cte_name} AS (SELECT {cte_columns} FROM {cte_table}{cte_where}) SELECT {columns} FROM {cte_name}{where};",
    # Transactions
    'begin': "BEGIN;",
    'commit': "COMMIT;",
    'rollback': "ROLLBACK;",
    # Utility
    'describe': "DESCRIBE {table};",
    'show_tables': "SHOW TABLES;",
    'show_databases': "SHOW DATABASES;",
    'use_database': "USE {database};",
    'explain': "EXPLAIN {query};",
}
