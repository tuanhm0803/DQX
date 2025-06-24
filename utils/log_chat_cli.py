#!/usr/bin/env python
"""
Command-line script to log chat interactions directly to the chat_log.txt file
"""
import sys
import os
import argparse
from datetime import datetime

def log_chat_to_file(user_message, assistant_response, log_file_path=None):
    """
    Log chat messages directly to the chat_log.txt file without going through the API.
    
    Args:
        user_message (str): The message from the user
        assistant_response (str): The response from the assistant
        log_file_path (str, optional): Path to the chat log file. If None, uses default location.
    """
    # If no log file path is provided, use the default location
    if log_file_path is None:
        # Get the path to the project root directory
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_file_path = os.path.join(project_dir, "chat_log.txt")
    
    # Get current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Format the log entry
    log_entry = f"\n[{timestamp}] USER: {user_message}\n"
    log_entry += f"[{timestamp}] ASSISTANT: {assistant_response}\n"
    log_entry += "-" * 80 + "\n"
    
    # Append the log entry to the chat log file
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(log_entry)
    
    print(f"Chat logged to {log_file_path}")

def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(description="Log chat interactions to a file")
    parser.add_argument("--user", "-u", required=True, help="User message")
    parser.add_argument("--assistant", "-a", required=True, help="Assistant response")
    parser.add_argument("--log-file", "-f", help="Path to log file. Default is chat_log.txt in project root.")
    
    args = parser.parse_args()
    
    log_chat_to_file(args.user, args.assistant, args.log_file)

if __name__ == "__main__":
    main()
