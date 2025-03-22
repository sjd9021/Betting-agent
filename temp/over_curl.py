# Extract GraphQL cURL commands from HAR file in an LLM-friendly format

import json
from pathlib import Path

# Load the HAR file
har_file = Path("/Users/samvitjatia/stake/betmade.har")
with har_file.open(encoding="utf-8") as f:
    har_data = json.load(f)

# Function to generate cURL command and info from HAR entry
def create_curl_command(entry):
    request = entry["request"]
    method = request["method"]
    url = request["url"]
    headers = {h["name"]: h["value"] for h in request.get("headers", [])}
    post_data = request.get("postData", {}).get("text", "")
    
    # Extract GraphQL info
    operation_info = {}
    if post_data:
        try:
            post_json = json.loads(post_data)
            operation_name = post_json.get("operationName", "Unknown")
            variables = post_json.get("variables", {})
            query = post_json.get("query", "")
            
            operation_info = {
                "operation_name": operation_name,
                "variables": variables,
                "query_snippet": query[:200] + "..." if len(query) > 200 else query
            }
        except:
            operation_info = {"error": "Could not parse GraphQL operation"}

    # Build curl command
    curl_parts = [f"curl '{url}'", f"-X {method}"]
    skip_headers = {"host", "content-length"}

    for name, value in headers.items():
        if name.lower() not in skip_headers:
            curl_parts.append(f"-H '{name}: {value}'")

    if post_data:
        curl_parts.append(f"--data-raw '{post_data}'")

    return {
        "url": url,
        "method": method,
        "graphql_info": operation_info,
        "curl": " \\\n  ".join(curl_parts)
    }

# Filter entries that are GraphQL requests
graphql_requests = []
for entry in har_data["log"]["entries"]:
    if "graphql" in entry["request"]["url"]:
        graphql_requests.append(create_curl_command(entry))

# Write to file in a structured JSON format
output_file = Path("graphql_requests2.json")
with output_file.open("w", encoding="utf-8") as f:
    json.dump(graphql_requests, f, indent=2)

# Also output a more concise summary for easier reading
with open("graphql_summary2.txt", "w", encoding="utf-8") as f:
    for i, req in enumerate(graphql_requests, 1):
        op_name = req["graphql_info"].get("operation_name", "Unknown")
        url = req["url"]
        variables = req["graphql_info"].get("variables", {})
        
        f.write(f"Request #{i}: {op_name}\n")
        f.write(f"URL: {url}\n")
        f.write(f"Variables: {json.dumps(variables, indent=2)}\n")
        f.write("-" * 80 + "\n\n")

print(f"Extracted {len(graphql_requests)} GraphQL requests")
print(f"Full details written to {output_file}")
print(f"Summary written to graphql_summary.txt")

