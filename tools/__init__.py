"""
Tools package for shaidow.

This package's __init__.py manages tool metadata like status messages and spinners.
"""

import json
import llm

# Lookup table for tool metadata
_tool_registry = {
    'Clock_local_time': {
        'during_status': "Checking the local time...",
        'after_status': "Checking the local time...",
        'spinner': "clock"
    },
    'Clock_utc_time': {
        'during_status': "Checking the UTC time...",
        'after_status': "Checking the UTC time...",
        'spinner': "clock"
    },
    'Clock_start_stopwatch': {
        'during_status': "Starting stopwatch...",
        'after_status': "Starting stopwatch...",
        'spinner': "clock"
    },
    'Clock_check_stopwatch': {
        'during_status': "Checking stopwatch...",
        'after_status': "Checking stopwatch...",
        'spinner': "clock"
    },
    'KnowledgeBase_search': {
        'during_status': "Searching knowledgebase for '{query}'...",
        'after_status': "Reading through {result_count} articles regarding '{query}'...",
        'spinner': "dots10"
    },
    'Web_search': {
        'during_status': "Searching web for '{query}'...",
        'after_status': "Skimming through {result_count} web results for '{query}'...",
        'spinner': "earth"
    },
    'Web_read_url': {
        'during_status': "Fetching '{url}'...",
        'after_status': "Reading '{url}'...",
        'spinner': "earth"
    }
}

def during_call_status_message(tool: llm.Tool, tool_call: llm.ToolCall):
    """
    Get the status message to be shown while a tool call is in progress
    """
    try:
        return _tool_registry[tool.name]['during_status'].format(**tool_call.arguments)
    except KeyError:
        return f"Using {tool.name} with arguments {tool_call.arguments}"

def after_call_status_message(tool: llm.Tool, tool_call: llm.ToolCall, tool_result: llm.ToolResult):
    """
    Get the status message to be shown after a tool call is complete and the model is thinking through its results
    """
    # Calculate result count
    try:
        result = json.loads(tool_result.output)
        result_count = len(result) if isinstance(result, list) else 1
    except (json.JSONDecodeError, TypeError):
        result_count = 0
    
    # Prepare template variables
    template_vars = {**tool_call.arguments, 'result_count': result_count}
    try:
        return _tool_registry[tool.name]['after_status'].format(**template_vars)
    except KeyError:
        return f"Reviewing output of {tool.name} call (arguments: {tool_call.arguments})"

def spinner(tool: llm.Tool):
    """
    Get the name of the Rich.Spinner to be shown while a tool is being used
    """
    try:
        return _tool_registry[tool.name]['spinner']
    except KeyError:
        return "dots10"
