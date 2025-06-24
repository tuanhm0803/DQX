"""
Logging utilities for DQX application

This module provides functionality for logging various types of information in the DQX application,
with a primary focus on chat logging between users and assistants. The logs are stored in text
files for easy access and review.

Usage:
    from utils.logger import log_chat
    
    # Log a conversation
    log_chat("User message", "Assistant response")

The logs are stored in the chat_log.txt file in the project root directory.
"""
import os
from datetime import datetime

def log_chat(user_message, assistant_response, custom_timestamp=None):
    """
    Log chat messages to the chat_log.txt file.
    
    This function records conversations between users and assistants in a structured format,
    with timestamps and clear separation between different conversations. Each entry includes
    the user's message followed by the assistant's response.
    
    Args:
        user_message (str): The message from the user
        assistant_response (str): The response from the assistant
        custom_timestamp (datetime, optional): Custom timestamp to use instead of current time
            Useful for back-dating logs or testing
    
    Returns:
        bool: True if logging was successful, False otherwise
    
    Example:
        log_chat("How do I query the database?", "You can use the SQL editor at /editor")
    """
    try:
        # Get the path to the chat log file (in the project root directory)
        chat_log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chat_log.txt")
        
        # Get current timestamp or use the provided one
        timestamp = custom_timestamp.strftime("%Y-%m-%d %H:%M:%S") if custom_timestamp else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Format the log entry with clear structure
        log_entry = f"\n[{timestamp}] USER: {user_message}\n"
        log_entry += f"[{timestamp}] ASSISTANT: {assistant_response}\n"
        log_entry += "-" * 80 + "\n"
        
        # Append the log entry to the chat log file
        with open(chat_log_path, "a", encoding="utf-8") as log_file:
            log_file.write(log_entry)
            
        return True
    except Exception as e:
        print(f"Error logging chat: {str(e)}")
        return False

def get_chat_log_path():
    """
    Get the path to the chat log file.
    
    Returns:
        str: The absolute path to the chat log file
    
    Example:
        log_path = get_chat_log_path()
        print(f"Logs are stored at: {log_path}")
    """
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "chat_log.txt")

def read_chat_logs(num_entries=None, from_date=None):
    """
    Read chat logs from the log file.
    
    Args:
        num_entries (int, optional): Number of most recent log entries to return.
            If None, returns all entries.
        from_date (datetime, optional): Return only entries from this date onwards.
            Format should be a datetime object.
    
    Returns:
        list: A list of dictionaries containing the log entries, where each
            dictionary has 'timestamp', 'user', and 'assistant' keys.
    
    Example:
        # Get the 10 most recent chat logs
        recent_logs = read_chat_logs(num_entries=10)
        
        # Get logs from a specific date
        from datetime import datetime
        date = datetime(2025, 6, 1)  # June 1, 2025
        logs = read_chat_logs(from_date=date)
    """
    try:
        chat_log_path = get_chat_log_path()
        
        if not os.path.exists(chat_log_path):
            return []
            
        with open(chat_log_path, "r", encoding="utf-8") as log_file:
            content = log_file.read()
            
        # Split log into individual entries (each entry ends with a separator line)
        entries = content.split("-" * 80)
        
        parsed_entries = []
        for entry in entries:
            if not entry.strip():
                continue
                
            # Parse each entry to extract timestamp, user message, and assistant response
            lines = entry.strip().split('\n')
            if len(lines) >= 2:  # At least user and assistant messages
                try:
                    # Extract timestamp, user message, and assistant response
                    user_line = lines[0]
                    assistant_line = lines[1] if len(lines) > 1 else ""
                    
                    # Extract timestamp
                    timestamp_str = user_line[user_line.find("[")+1:user_line.find("]")]
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    
                    # Skip if from_date is specified and the entry is before that date
                    if from_date and timestamp < from_date:
                        continue
                        
                    # Extract user message and assistant response
                    user_message = user_line[user_line.find("USER: ")+6:].strip()
                    assistant_response = assistant_line[assistant_line.find("ASSISTANT: ")+11:].strip() if assistant_line else ""
                    
                    # Add to parsed entries
                    parsed_entries.append({
                        'timestamp': timestamp,
                        'user': user_message,
                        'assistant': assistant_response
                    })
                except Exception:
                    # Skip malformed entries
                    continue
        
        # Sort by timestamp (newest first)
        parsed_entries.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Limit to num_entries if specified
        if num_entries:
            parsed_entries = parsed_entries[:num_entries]
            
        return parsed_entries
    except Exception as e:
        print(f"Error reading chat logs: {str(e)}")
        return []

def clear_chat_logs():
    """
    Clear all chat logs by removing the log file.
    
    Returns:
        bool: True if successful, False otherwise
    
    Example:
        if clear_chat_logs():
            print("All logs have been cleared")
        else:
            print("Failed to clear logs")
    """
    try:
        chat_log_path = get_chat_log_path()
        
        if os.path.exists(chat_log_path):
            os.remove(chat_log_path)
            
        return True
    except Exception as e:
        print(f"Error clearing chat logs: {str(e)}")
        return False
