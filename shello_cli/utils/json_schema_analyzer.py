"""JSON schema analyzer - generates jq paths with data types from JSON input"""
import json


def json_to_jq_paths(json_output):
    """Generate jq paths with data types from JSON input"""
    
    def extract_paths(obj, jq_path=""):
        """Recursively extract paths from JSON object"""
        paths = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_jq_path = f"{jq_path}.{key}" if jq_path else f".{key}"
                
                if isinstance(value, dict):
                    # Nested object - recurse deeper
                    paths.extend(extract_paths(value, new_jq_path))
                
                elif isinstance(value, list):
                    # Array field
                    paths.append(f"{new_jq_path}[] | array[{len(value)}]")
                    
                    # If array contains primitives, add array item type
                    if value and not isinstance(value[0], (dict, list)):
                        item_type = type(value[0]).__name__
                        if item_type == 'str':
                            paths.append(f"{new_jq_path}[] | array_item_str")
                        elif item_type == 'int':
                            paths.append(f"{new_jq_path}[] | array_item_int")
                        elif item_type == 'float':
                            paths.append(f"{new_jq_path}[] | array_item_float")
                        elif item_type == 'bool':
                            paths.append(f"{new_jq_path}[] | array_item_bool")
                    
                    # If array contains objects, analyze their structure
                    if value and isinstance(value[0], dict):
                        paths.extend(extract_paths(value[0], f"{new_jq_path}[]"))
                
                else:
                    # Leaf node
                    type_name = type(value).__name__
                    paths.append(f"{new_jq_path} | {type_name}")
        
        elif isinstance(obj, list) and obj:
            # Root is array - analyze first item
            paths.extend(extract_paths(obj[0], ".[]"))
        
        return paths
    
    try:
        data = json.loads(json_output)
        paths = extract_paths(data)
        
        # Sort paths for consistent output
        paths.sort()
        
        # Add header and return formatted output
        output_lines = ["jq path | data type", ""] + paths
        return "\n".join(output_lines)
    
    except json.JSONDecodeError:
        return "Error: Invalid JSON format"
    except Exception as e:
        return f"Error analyzing JSON: {str(e)}"


# Example usage
if __name__ == "__main__":
    sample_json = '''{
        "Functions": [
            {
                "LoggingConfig": {
                    "LogFormat": "Text",
                    "LogGroup": "/aws/lambda/SC-546928918642-pp-zb4ura-Product-Deployment-Function-7115JuFHSrvX"
                },
                "FunctionName": "product-factory-offer-event-dev2",
                "VpcConfig": {
                    "SubnetIds": [
                        "subnet-018509b8d177eb0df",
                        "subnet-088ccc7bfce79cf9c",
                        "subnet-efca1b027a2b41a2f"
                    ],
                    "VpcId": "vpc-09af8c2b1b585ebec",
                    "Ipv6AllowedForDualStack": false
                },
                "Configuration": {
                    "Architectures": ["x86_64", "arm64"],
                    "CodeSha256": "abc123def456",
                    "CodeSize": 1024,
                    "Runtime": "python3.9"
                },
                "Tags": {
                    "aws:cloudformation:logical-id": "MyFunction",
                    "aws:cloudformation:stack-name": "my-stack",
                    "aws:cloudformation:stack-id": "arn:aws:cloudformation:us-east-1:123456789012:stack/my-stack/12345",
                    "aws:servicecatalog:portfolioArn": "arn:aws:servicecatalog:us-east-1:123456789012:portfolio/port-12345",
                    "aws:servicecatalog:productArn": "arn:aws:servicecatalog:us-east-1:123456789012:product/prod-12345"
                },
                "Version": "$LATEST",
                "LastModified": "2023-09-15T10:30:00.000+0000"
            }
        ]
    }'''
    
    result = json_to_jq_paths(sample_json)
    print(result)
