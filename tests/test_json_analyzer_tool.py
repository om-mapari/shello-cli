"""
Tests for the JSON analyzer tool.
"""

import pytest
from hypothesis import given, strategies as st
from shello_cli.tools.json_analyzer_tool import JsonAnalyzerTool


class TestJsonAnalyzerToolUnitTests:
    """Unit tests for JSON analyzer tool"""
    
    def test_analyze_simple_object(self):
        """Test analyzing a simple JSON object"""
        tool = JsonAnalyzerTool()
        json_input = '{"name": "John", "age": 30, "active": true}'
        
        result = tool.analyze(json_input)
        
        assert result.success is True
        assert result.error is None
        assert ".name | string" in result.output
        assert ".age | number" in result.output
        assert ".active | boolean" in result.output
    
    def test_analyze_nested_object(self):
        """Test analyzing nested JSON objects"""
        tool = JsonAnalyzerTool()
        json_input = '{"user": {"name": "John", "email": "john@example.com"}}'
        
        result = tool.analyze(json_input)
        
        assert result.success is True
        assert ".user.name | string" in result.output
        assert ".user.email | string" in result.output
    
    def test_analyze_array(self):
        """Test analyzing JSON with arrays"""
        tool = JsonAnalyzerTool()
        json_input = '{"items": ["apple", "banana", "cherry"]}'
        
        result = tool.analyze(json_input)
        
        assert result.success is True
        assert ".items[] | array[3]" in result.output
        assert ".items[] | array_item_str" in result.output
    
    def test_analyze_array_of_objects(self):
        """Test analyzing array of objects"""
        tool = JsonAnalyzerTool()
        json_input = '{"users": [{"name": "John", "age": 30}]}'
        
        result = tool.analyze(json_input)
        
        assert result.success is True
        assert ".users[] | array[1]" in result.output
        assert ".users[].name | string" in result.output
        assert ".users[].age | number" in result.output
    
    def test_analyze_invalid_json(self):
        """Test handling invalid JSON"""
        tool = JsonAnalyzerTool()
        json_input = '{"invalid": json}'
        
        result = tool.analyze(json_input)
        
        assert result.success is False
        assert result.output is None
        assert "Invalid JSON format" in result.error
    
    def test_analyze_empty_object(self):
        """Test analyzing empty JSON object"""
        tool = JsonAnalyzerTool()
        json_input = '{}'
        
        result = tool.analyze(json_input)
        
        assert result.success is True
        # Empty object should have header but no paths
        assert "jq path | data type" in result.output
    
    def test_analyze_null_value(self):
        """Test analyzing JSON with null values"""
        tool = JsonAnalyzerTool()
        json_input = '{"value": null}'
        
        result = tool.analyze(json_input)
        
        assert result.success is True
        assert ".value | null" in result.output
    
    def test_analyze_mixed_types_array(self):
        """Test analyzing array with numbers"""
        tool = JsonAnalyzerTool()
        json_input = '{"numbers": [1, 2, 3, 4, 5]}'
        
        result = tool.analyze(json_input)
        
        assert result.success is True
        assert ".numbers[] | array[5]" in result.output
        assert ".numbers[] | array_item_int" in result.output
    
    def test_analyze_root_array(self):
        """Test analyzing JSON where root is an array"""
        tool = JsonAnalyzerTool()
        json_input = '[{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]'
        
        result = tool.analyze(json_input)
        
        assert result.success is True
        assert ".[] | array[2]" in result.output
        assert ".[].id | number" in result.output
        assert ".[].name | string" in result.output
    
    def test_analyze_aws_s3_buckets_example(self):
        """Test analyzing AWS S3 list-buckets output structure"""
        tool = JsonAnalyzerTool()
        json_input = '''
        {
            "Buckets": [
                {
                    "Name": "my-bucket",
                    "CreationDate": "2023-01-01T00:00:00.000Z"
                }
            ],
            "Owner": {
                "DisplayName": "owner",
                "ID": "abc123"
            }
        }
        '''
        
        result = tool.analyze(json_input)
        
        assert result.success is True
        assert ".Buckets[] | array[1]" in result.output
        assert ".Buckets[].Name | string" in result.output
        assert ".Buckets[].CreationDate | string" in result.output
        assert ".Owner.DisplayName | string" in result.output
        assert ".Owner.ID | string" in result.output


class TestJsonAnalyzerToolProperties:
    """Property-based tests for JSON analyzer tool"""
    
    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        values=st.one_of(
            st.text(max_size=50),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.booleans(),
            st.none()
        ),
        min_size=1,
        max_size=10
    ))
    def test_property_analyze_always_succeeds_for_valid_json(self, json_dict):
        """Property: Analyzing valid JSON always succeeds"""
        tool = JsonAnalyzerTool()
        import json
        json_input = json.dumps(json_dict)
        
        result = tool.analyze(json_input)
        
        assert result.success is True
        assert result.error is None
        assert result.output is not None
        assert "jq path | data type" in result.output
    
    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        values=st.text(max_size=50),
        min_size=1,
        max_size=5
    ))
    def test_property_all_keys_appear_in_output(self, json_dict):
        """Property: All keys from JSON appear in the output paths"""
        tool = JsonAnalyzerTool()
        import json
        json_input = json.dumps(json_dict)
        
        result = tool.analyze(json_input)
        
        assert result.success is True
        for key in json_dict.keys():
            assert f".{key}" in result.output
