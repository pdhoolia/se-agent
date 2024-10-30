import pytest
from unittest.mock import patch
from se_agent.repository_analyzer.package_summary import generate_package_summary

@pytest.fixture
def package_details_content():
    """Fixture to provide sample package details content."""
    return "# Package Details\nSome detailed content about the package."


@patch('se_agent.repository_analyzer.package_summary.call_llm_for_task')
def test_generate_package_summary(mock_llm_call, package_details_content):
    """Test generating a single package summary with mocked LLM call."""
    
    # Define mock response for the LLM call
    mock_llm_call.return_value.content = "```python\nThis is a package summary.\n```"
    
    # Call the generate_package_summary function
    package_name = "package1"
    summary = generate_package_summary(package_name, package_details_content)
    
    # Check the returned summary content
    assert "This is a package summary." in summary
    # Ensure that the code fence has been removed from the summary
    assert "```" not in summary


@patch('se_agent.repository_analyzer.package_summary.call_llm_for_task')
def test_generate_package_summary_handles_code_fence(mock_llm_call, package_details_content):
    """Test that the function properly handles summaries wrapped in code fences."""
    
    # Define a mock response that simulates a code block fence
    mock_llm_call.return_value.content = "```python\n# This is a summary with code fence\n```"
    
    # Call the generate_package_summary function
    package_name = "package_with_code"
    summary = generate_package_summary(package_name, package_details_content)
    
    # Check the content inside the code fence is extracted correctly
    assert "# This is a summary with code fence" in summary
    # Ensure that the code fence has been removed from the summary
    assert "```" not in summary


@patch('se_agent.repository_analyzer.package_summary.call_llm_for_task')
def test_generate_package_summary_raises_error(mock_llm_call, package_details_content):
    """Test that the function raises an error if the LLM call fails."""
    
    # Simulate an error during the LLM call
    mock_llm_call.side_effect = Exception("LLM service error")
    
    package_name = "error_package"
    
    # Expect the function to raise a RuntimeError
    with pytest.raises(RuntimeError, match="Error generating summary for package error_package"):
        generate_package_summary(package_name, package_details_content)
