"""
API call domain templates for NLP2CMD.

Contains curl, httpie, wget, REST API templates.
"""

API_TEMPLATES = {
    # curl GET
    'get': "curl -s {url}",
    'get_json': "curl -s -H 'Content-Type: application/json' {url}",
    'get_auth': "curl -s -H 'Authorization: Bearer {token}' {url}",
    'get_headers': "curl -sI {url}",
    'get_verbose': "curl -v {url}",
    # curl POST
    'post_json': "curl -s -X POST -H 'Content-Type: application/json' -d '{data}' {url}",
    'post_form': "curl -s -X POST -F '{field}={value}' {url}",
    'post_file': "curl -s -X POST -F 'file=@{file}' {url}",
    # curl PUT/PATCH/DELETE
    'put': "curl -s -X PUT -H 'Content-Type: application/json' -d '{data}' {url}",
    'patch': "curl -s -X PATCH -H 'Content-Type: application/json' -d '{data}' {url}",
    'delete': "curl -s -X DELETE {url}",
    # curl advanced
    'download': "curl -LO {url}",
    'download_output': "curl -L -o {output} {url}",
    'upload': "curl -s -X POST -F 'file=@{file}' {url}",
    'retry': "curl -s --retry {count} --retry-delay {delay} {url}",
    'timeout': "curl -s --connect-timeout {timeout} {url}",
    'follow_redirect': "curl -sL {url}",
    'cookie': "curl -s -b '{cookie}' {url}",
    'basic_auth': "curl -s -u {user}:{password} {url}",
    # wget
    'wget_download': "wget {url}",
    'wget_output': "wget -O {output} {url}",
    'wget_recursive': "wget -r -l {depth} {url}",
    'wget_mirror': "wget --mirror --convert-links --no-parent {url}",
    'wget_continue': "wget -c {url}",
    # httpie
    'http_get': "http GET {url}",
    'http_post': "http POST {url} {data}",
    'http_put': "http PUT {url} {data}",
    'http_delete': "http DELETE {url}",
    'http_auth': "http -a {user}:{password} GET {url}",
    # jq processing
    'jq_parse': "curl -s {url} | jq '{filter}'",
    'jq_pretty': "curl -s {url} | jq '.'",
    'jq_keys': "curl -s {url} | jq 'keys'",
    'jq_length': "curl -s {url} | jq 'length'",
    'jq_select': "curl -s {url} | jq '.[] | select({condition})'",
    # API testing
    'health_check': "curl -sf {url}/health && echo 'OK' || echo 'FAIL'",
    'status_code': "curl -o /dev/null -s -w '%{{http_code}}' {url}",
    'response_time': "curl -o /dev/null -s -w '%{{time_total}}' {url}",
    'benchmark_api': "ab -n {requests} -c {concurrency} {url}",
    # GraphQL
    'graphql_query': "curl -s -X POST -H 'Content-Type: application/json' -d '{{\"query\": \"{query}\"}}' {url}",
    'graphql_mutation': "curl -s -X POST -H 'Content-Type: application/json' -d '{{\"query\": \"mutation {{ {mutation} }}\"}}' {url}",
    # WebSocket
    'websocket_test': "websocat {url}",
    'websocket_curl': "curl --include --no-buffer -H 'Connection: Upgrade' -H 'Upgrade: websocket' {url}",
}
