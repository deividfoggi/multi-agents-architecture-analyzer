import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
from local_template_client import LocalTemplateClient

class TestLocalTemplateClient:
    """Test suite for LocalTemplateClient"""
    
    def test_init_with_default_path(self):
        """Test initialization with default essay.yaml path"""
        # Create a temporary essay.yaml file
        with tempfile.NamedTemporaryFile(mode='w', suffix='essay.yaml', delete=False) as tmp_file:
            tmp_file.write("test: content")
            tmp_path = tmp_file.name
        
        try:
            # Mock the default path resolution
            with patch('local_template_client.Path.__file__', new=tmp_path):
                with patch.object(Path, 'parent', new_callable=lambda: Path(os.path.dirname(tmp_path))):
                    client = LocalTemplateClient()
                    assert client.template_file_path.name.endswith('essay.yaml')
        finally:
            os.unlink(tmp_path)
    
    def test_init_with_custom_path(self):
        """Test initialization with custom template path"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
            tmp_file.write("test: content")
            tmp_path = tmp_file.name
        
        try:
            client = LocalTemplateClient(template_file_path=tmp_path)
            assert str(client.template_file_path) == tmp_path
        finally:
            os.unlink(tmp_path)
    
    def test_init_with_nonexistent_file(self):
        """Test initialization fails with nonexistent file"""
        with pytest.raises(FileNotFoundError):
            LocalTemplateClient(template_file_path="/nonexistent/path/template.yaml")
    
    def test_get_template_default_file(self):
        """Test getting template content from default file"""
        test_content = """
name: TestTemplate
template: |
  This is a test template
  with multiple lines
description: Test template
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
            tmp_file.write(test_content)
            tmp_path = tmp_file.name
        
        try:
            client = LocalTemplateClient(template_file_path=tmp_path)
            content = client.get_template()
            assert content == test_content
        finally:
            os.unlink(tmp_path)
    
    def test_get_template_with_file_name(self):
        """Test getting template content from specified file"""
        test_content = "test: specific_file"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
            tmp_file.write(test_content)
            tmp_path = tmp_file.name
        
        # Create default file (won't be used)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as default_file:
            default_file.write("default: content")
            default_path = default_file.name
        
        try:
            client = LocalTemplateClient(template_file_path=default_path)
            content = client.get_template(file_name=tmp_path)
            assert content == test_content
        finally:
            os.unlink(tmp_path)
            os.unlink(default_path)
    
    def test_get_template_nonexistent_file(self):
        """Test getting template from nonexistent file raises FileNotFoundError"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
            tmp_file.write("test: content")
            tmp_path = tmp_file.name
        
        try:
            client = LocalTemplateClient(template_file_path=tmp_path)
            with pytest.raises(FileNotFoundError):
                client.get_template(file_name="/nonexistent/file.yaml")
        finally:
            os.unlink(tmp_path)
    
    def test_get_template_permission_error(self):
        """Test permission error handling"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
            tmp_file.write("test: content")
            tmp_path = tmp_file.name
        
        try:
            client = LocalTemplateClient(template_file_path=tmp_path)
            
            # Mock permission error
            with patch('builtins.open', side_effect=PermissionError("Access denied")):
                with pytest.raises(FileNotFoundError, match="Permission denied"):
                    client.get_template()
        finally:
            os.unlink(tmp_path)
    
    def test_get_template_unicode_error(self):
        """Test unicode decode error handling"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
            tmp_file.write("test: content")
            tmp_path = tmp_file.name
        
        try:
            client = LocalTemplateClient(template_file_path=tmp_path)
            
            # Mock unicode decode error
            with patch('builtins.open', side_effect=UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid')):
                with pytest.raises(ValueError, match="Invalid file encoding"):
                    client.get_template()
        finally:
            os.unlink(tmp_path)
    
    def test_env_var_template_path(self):
        """Test template path from environment variable"""
        test_content = "env_test: content"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
            tmp_file.write(test_content)
            tmp_path = tmp_file.name
        
        try:
            with patch.dict(os.environ, {'LOCAL_TEMPLATE_FILE_PATH': tmp_path}):
                client = LocalTemplateClient()
                content = client.get_template()
                assert content == test_content
        finally:
            os.unlink(tmp_path)
    
    def test_relative_path_resolution(self):
        """Test relative path resolution"""
        test_content = "relative: test"
        
        # Create temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            template_file = Path(temp_dir) / "test_template.yaml"
            template_file.write_text(test_content)
            
            # Mock the project root to be temp_dir
            with patch('local_template_client.Path.__file__', new=str(Path(temp_dir) / 'local_template_client.py')):
                client = LocalTemplateClient(template_file_path="test_template.yaml")
                content = client.get_template()
                assert content == test_content

if __name__ == "__main__":
    pytest.main([__file__])