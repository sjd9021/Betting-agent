import json
import re
from pathlib import Path

# Load the HAR file
har_path = Path("/Users/samvitjatia/stake/stake.games.har")
with har_path.open("r", encoding="utf-8") as f:
    har_data = json.load(f)

# Extract all GraphQL requests and construct cURL commands with schema info
graphql_curls = []
schema_info = []

for entry in har_data["log"]["entries"]:
    request = entry["request"]
    response = entry.get("response", {})
    url = request["url"]

    # Only process GraphQL requests
    if "graphql" not in url:
        continue

    method = request["method"]
    headers = {h["name"]: h["value"] for h in request["headers"]}
    post_data = request.get("postData", {}).get("text", "")
    
    # Try to parse the GraphQL operation info
    operation_info = {}
    if post_data:
        try:
            post_json = json.loads(post_data)
            query = post_json.get("query", "")
            variables = post_json.get("variables", {})
            
            # Extract operation name using regex
            operation_match = re.search(r'(query|mutation)\s+(\w+)', query)
            operation_name = operation_match.group(2) if operation_match else "Unknown"
            operation_type = operation_match.group(1) if operation_match else "query"
            
            operation_info = {
                "operation_name": operation_name,
                "operation_type": operation_type,
                "variables_schema": {k: type(v).__name__ for k, v in variables.items()},
            }
            
            # Try to extract response schema if available
            response_content = response.get("content", {})
            response_text = response_content.get("text", "{}")
            
            if response_text:
                try:
                    response_json = json.loads(response_text)
                    data = response_json.get("data", {})
                    if data:
                        # Create simplified schema from first level of response
                        response_schema = {k: type(v).__name__ for k, v in data.items()}
                        operation_info["response_schema"] = response_schema
                except:
                    operation_info["response_schema"] = "Could not parse response"
        except:
            operation_info = {"error": "Could not parse GraphQL operation"}

    # Build the curl command
    curl_parts = [f"curl '{url}'"]
    curl_parts.append(f"-X {method}")

    for k, v in headers.items():
        # Skip headers that are typically auto-set by curl
        if k.lower() in {"host", "content-length"}:
            continue
        curl_parts.append(f"-H '{k}: {v}'")

    if post_data:
        curl_parts.append(f"--data-raw '{post_data}'")

    curl_command = " \\\n  ".join(curl_parts)
    graphql_curls.append(curl_command)
    
    # Add schema info for this request
    schema_info.append({
        "curl": curl_command,  # Include the full curl command
        "schema_info": operation_info
    })

# Write curl commands to file
output_path = Path("stake_graphql_curls.txt")
with output_path.open("w", encoding="utf-8") as f:
    f.write("\n\n".join(graphql_curls))

# Write schema information to file
schema_path = Path("stake_graphql_schemas.json")
with schema_path.open("w", encoding="utf-8") as f:
    json.dump(schema_info, f, indent=2)

print(f"Curl commands written to {output_path}")
print(f"Schema information written to {schema_path}")
