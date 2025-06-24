#!/usr/bin/env python
"""
Examples of how to use the DQX logging utilities.

This script demonstrates various ways to use the logging functions
from the logger module for different use cases.
"""
from datetime import datetime, timedelta
from logger import log_chat, read_chat_logs, clear_chat_logs, get_chat_log_path

def basic_logging_example():
    """Basic example of logging a chat conversation."""
    print("=== Basic Logging Example ===")
    
    # Log a simple chat conversation
    success = log_chat(
        "How do I query the database?",
        "You can use the SQL Editor at /editor to write and execute SQL queries."
    )
    
    if success:
        print("Successfully logged a basic chat conversation.")
    else:
        print("Failed to log the conversation.")
    
    print(f"Log file location: {get_chat_log_path()}")
    print()

def custom_timestamp_example():
    """Example of logging with a custom timestamp."""
    print("=== Custom Timestamp Example ===")
    
    # Log a conversation with a custom timestamp (yesterday)
    yesterday = datetime.now() - timedelta(days=1)
    success = log_chat(
        "What features does this application have?",
        "The application includes database exploration, SQL editor, scheduling, and chat logging.",
        custom_timestamp=yesterday
    )
    
    if success:
        print(f"Successfully logged a conversation with timestamp: {yesterday.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("Failed to log the conversation.")
    print()

def read_logs_example():
    """Example of reading and displaying chat logs."""
    print("=== Read Logs Example ===")
    
    # Read the 5 most recent logs
    logs = read_chat_logs(num_entries=5)
    
    if logs:
        print(f"Retrieved {len(logs)} log entries:")
        for i, log in enumerate(logs, 1):
            print(f"Log #{i}:")
            print(f"  Timestamp: {log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  User: {log['user']}")
            print(f"  Assistant: {log['assistant']}")
            print()
    else:
        print("No log entries found.")
    print()

def date_filtered_logs_example():
    """Example of filtering logs by date."""
    print("=== Date Filtered Logs Example ===")
    
    # Get logs from the last 24 hours
    yesterday = datetime.now() - timedelta(days=1)
    logs = read_chat_logs(from_date=yesterday)
    
    print(f"Logs from the past 24 hours: {len(logs)} entries found")
    print()

def clear_logs_example():
    """Example of clearing the logs (commented out by default)."""
    print("=== Clear Logs Example ===")
    print("NOTE: This example is commented out to prevent accidental log deletion.")
    
    # Uncomment the following code to test clearing logs
    # if input("Are you sure you want to clear all logs? (y/n): ").lower() == 'y':
    #     if clear_chat_logs():
    #         print("All logs have been cleared.")
    #     else:
    #         print("Failed to clear logs.")
    # else:
    #     print("Log clearing canceled.")
    print()

def main():
    """Run all the examples."""
    print("DQX Logger Examples")
    print("==================\n")
    
    basic_logging_example()
    custom_timestamp_example()
    read_logs_example()
    date_filtered_logs_example()
    clear_logs_example()
    
    print("All examples completed.")

if __name__ == "__main__":
    main()
