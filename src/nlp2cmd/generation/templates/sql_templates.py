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
    'explain_analyze': "EXPLAIN ANALYZE {query};",
    # GROUP BY + HAVING
    'group_having': "SELECT {columns}, COUNT(*) AS cnt FROM {table}{where} GROUP BY {group_columns} HAVING COUNT(*) {operator} {value};",
    'group_sum': "SELECT {group_column}, SUM({column}) AS total FROM {table}{where} GROUP BY {group_column}{order};",
    'group_avg': "SELECT {group_column}, AVG({column}) AS avg_val FROM {table}{where} GROUP BY {group_column}{order};",
    # CASE
    'case_when': "SELECT {columns}, CASE WHEN {condition1} THEN {result1} WHEN {condition2} THEN {result2} ELSE {default} END AS {alias} FROM {table};",
    # UNION
    'union': "SELECT {columns} FROM {table1}{where1} UNION SELECT {columns} FROM {table2}{where2};",
    'union_all': "SELECT {columns} FROM {table1}{where1} UNION ALL SELECT {columns} FROM {table2}{where2};",
    # Date functions
    'date_range': "SELECT {columns} FROM {table} WHERE {date_column} BETWEEN '{start_date}' AND '{end_date}';",
    'date_extract': "SELECT EXTRACT({part} FROM {date_column}) AS {alias} FROM {table};",
    'date_diff': "SELECT DATEDIFF({date1}, {date2}) AS diff FROM {table};",
    'now': "SELECT NOW();",
    'current_date': "SELECT CURRENT_DATE;",
    # String functions
    'concat': "SELECT CONCAT({col1}, ' ', {col2}) AS {alias} FROM {table};",
    'like': "SELECT {columns} FROM {table} WHERE {column} LIKE '{pattern}';",
    'ilike': "SELECT {columns} FROM {table} WHERE {column} ILIKE '{pattern}';",
    'upper': "SELECT UPPER({column}) FROM {table};",
    'lower': "SELECT LOWER({column}) FROM {table};",
    'trim': "SELECT TRIM({column}) FROM {table};",
    'substring': "SELECT SUBSTRING({column}, {start}, {length}) FROM {table};",
    # Permissions
    'grant': "GRANT {privileges} ON {table} TO {user};",
    'revoke': "REVOKE {privileges} ON {table} FROM {user};",
    'create_user': "CREATE USER {username} WITH PASSWORD '{password}';",
    'drop_user': "DROP USER {username};",
    # Insert from select
    'insert_select': "INSERT INTO {target_table} ({columns}) SELECT {columns} FROM {source_table}{where};",
    # Upsert
    'upsert_pg': "INSERT INTO {table} ({columns}) VALUES ({values}) ON CONFLICT ({conflict_column}) DO UPDATE SET {set_clause};",
    'upsert_mysql': "INSERT INTO {table} ({columns}) VALUES ({values}) ON DUPLICATE KEY UPDATE {set_clause};",
    # Backup / Restore
    'pg_dump': "pg_dump -U {user} -d {database} -f {output_file}",
    'pg_restore': "psql -U {user} -d {database} -f {input_file}",
    'mysql_dump': "mysqldump -u {user} -p {database} > {output_file}",
    'mysql_restore': "mysql -u {user} -p {database} < {input_file}",
    # PostgreSQL specific
    'pg_size': "SELECT pg_size_pretty(pg_database_size('{database}'));",
    'pg_tables': "SELECT tablename FROM pg_tables WHERE schemaname = 'public';",
    'pg_columns': "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}';",
    'pg_connections': "SELECT * FROM pg_stat_activity;",
    'pg_locks': "SELECT * FROM pg_locks;",
    # SQLite specific
    'sqlite_tables': ".tables",
    'sqlite_schema': ".schema {table}",
    'sqlite_import_csv': ".import {file} {table}",
    'sqlite_export_csv': ".mode csv\n.output {file}\nSELECT * FROM {table};",
}
