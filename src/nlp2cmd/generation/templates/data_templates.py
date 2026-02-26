"""
Data processing domain templates for NLP2CMD.

Contains jq, csvkit, awk, data pipeline templates.
"""

DATA_TEMPLATES = {
    # jq — JSON processing
    'jq_pretty': "jq '.' {file}",
    'jq_keys': "jq 'keys' {file}",
    'jq_select': "jq '.[] | select(.{field} {operator} {value})' {file}",
    'jq_map': "jq '[.[] | .{field}]' {file}",
    'jq_filter': "jq '{filter}' {file}",
    'jq_length': "jq 'length' {file}",
    'jq_sort': "jq 'sort_by(.{field})' {file}",
    'jq_group': "jq 'group_by(.{field})' {file}",
    'jq_unique': "jq 'unique_by(.{field})' {file}",
    'jq_flatten': "jq 'flatten' {file}",
    'jq_to_csv': "jq -r '.[] | [.{fields}] | @csv' {file}",
    # csvkit
    'csv_info': "csvstat {file}",
    'csv_head': "csvlook {file} | head -n {lines}",
    'csv_columns': "csvcut -n {file}",
    'csv_select_cols': "csvcut -c {columns} {file}",
    'csv_filter': "csvgrep -c {column} -m '{pattern}' {file}",
    'csv_sort': "csvsort -c {column} {file}",
    'csv_join': "csvjoin -c {column} {file1} {file2}",
    'csv_to_json': "csvjson {file}",
    'csv_sql': "csvsql --query '{query}' {file}",
    'csv_to_sqlite': "csvsql --db sqlite:///{database} --insert {file}",
    # awk processing
    'awk_columns': "awk '{{print ${columns}}}' {file}",
    'awk_sum': "awk '{{s+=${column}}} END {{print s}}' {file}",
    'awk_avg': "awk '{{s+=${column}; c++}} END {{print s/c}}' {file}",
    'awk_count': "awk 'END {{print NR}}' {file}",
    'awk_filter': "awk '${column} {operator} {value}' {file}",
    'awk_unique': "awk '!seen[${column}]++' {file}",
    'awk_group_count': "awk '{{count[${column}]++}} END {{for (k in count) print k, count[k]}}' {file}",
    # sed processing
    'sed_replace': "sed 's/{pattern}/{replacement}/g' {file}",
    'sed_replace_inplace': "sed -i 's/{pattern}/{replacement}/g' {file}",
    'sed_delete_line': "sed '{line}d' {file}",
    'sed_delete_pattern': "sed '/{pattern}/d' {file}",
    'sed_insert': "sed '{line}i\\{text}' {file}",
    # sort / uniq
    'sort_file': "sort {file}",
    'sort_numeric': "sort -n {file}",
    'sort_reverse': "sort -r {file}",
    'sort_column': "sort -t'{delimiter}' -k{column} {file}",
    'sort_unique': "sort -u {file}",
    'uniq_count': "sort {file} | uniq -c | sort -rn",
    'uniq_duplicates': "sort {file} | uniq -d",
    # xsv (fast CSV)
    'xsv_stats': "xsv stats {file}",
    'xsv_count': "xsv count {file}",
    'xsv_headers': "xsv headers {file}",
    'xsv_select': "xsv select {columns} {file}",
    'xsv_search': "xsv search '{pattern}' {file}",
    'xsv_sort': "xsv sort -s {column} {file}",
    'xsv_frequency': "xsv frequency -s {column} {file}",
    'xsv_join': "xsv join {column1} {file1} {column2} {file2}",
    # sqlite
    'sqlite_query': "sqlite3 {database} '{query}'",
    'sqlite_tables': "sqlite3 {database} '.tables'",
    'sqlite_schema': "sqlite3 {database} '.schema {table}'",
    'sqlite_import_csv': "sqlite3 {database} '.mode csv' '.import {file} {table}'",
    'sqlite_export_csv': "sqlite3 -header -csv {database} '{query}' > {output}",
    # Python one-liners for data
    'python_json_pretty': "python3 -m json.tool {file}",
    'python_csv_info': "python3 -c \"import pandas as pd; print(pd.read_csv('{file}').describe())\"",
    'python_json_to_csv': "python3 -c \"import pandas as pd, json; pd.DataFrame(json.load(open('{input}'))).to_csv('{output}', index=False)\"",
}
