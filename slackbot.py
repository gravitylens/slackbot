#!/usr/bin/env python3
"""
GESBot - A pipeline-friendly Slack bot that sends messages.
Usage: 
  echo "message text" | python slackbot.py [destination]
  python slackbot.py [destination] < message.json
"""

import os
import sys
import json
import argparse
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Load environment variables with fallback logic
def load_env_with_fallback():
    """Load .env file checking local first, then home directory for required values."""
    # Try local .env first
    if os.path.exists('.env'):
        load_dotenv('.env')
    
    # Check if we have the required SLACK_BOT_TOKEN
    if not os.getenv('SLACK_BOT_TOKEN'):
        # If not, try home directory .env
        home_env = os.path.expanduser('~/.env')
        if os.path.exists(home_env):
            load_dotenv(home_env)
    
    # Final fallback to default behavior
    if not os.getenv('SLACK_BOT_TOKEN'):
        load_dotenv()

# Load environment variables
load_env_with_fallback()

class SlackBot:
    def __init__(self):
        # Initialize the Slack client with your bot token
        self.client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))
        self.default_channel = os.getenv('SLACK_CHANNEL', '#general')
    
    def send_message(self, text, channel=None):
        """
        Send a message to a Slack channel.
        
        Args:
            text (str): The message text to send
            channel (str): The channel to send to (defaults to env SLACK_CHANNEL)
        
        Returns:
            dict: Response from Slack API
        """
        target_channel = channel or self.default_channel
        
        try:
            response = self.client.chat_postMessage(
                channel=target_channel,
                text=text,
                mrkdwn=True
            )
            
            print(f"✅ Message sent to {target_channel}", file=sys.stderr)
            return response
            
        except SlackApiError as e:
            error_msg = e.response['error']
            if error_msg == 'missing_scope':
                print(f"❌ Error sending message: {error_msg}", file=sys.stderr)
                print(f"💡 Your token needs 'chat:write' scope to send messages", file=sys.stderr)
            elif error_msg == 'channel_not_found':
                print(f"❌ Channel {target_channel} not found or bot doesn't have access", file=sys.stderr)
            elif error_msg == 'not_in_channel':
                print(f"❌ GESBot is not a member of {target_channel}", file=sys.stderr)
                print(f"💡 Add GESBot to the channel first: /invite @GESBot", file=sys.stderr)
            else:
                print(f"❌ Error sending message: {error_msg}", file=sys.stderr)
            return None
    
    def send_message_with_blocks(self, blocks, text="", channel=None):
        """
        Send a formatted message with Slack blocks.
        
        Args:
            blocks (list): List of Slack block elements
            text (str): Fallback text for notifications
            channel (str): The channel to send to
        
        Returns:
            dict: Response from Slack API
        """
        target_channel = channel or self.default_channel
        
        try:
            response = self.client.chat_postMessage(
                channel=target_channel,
                text=text,
                blocks=blocks,
                mrkdwn=True
            )
            
            print(f"✅ Formatted message sent to {target_channel}", file=sys.stderr)
            return response
            
        except SlackApiError as e:
            error_msg = e.response['error']
            if error_msg == 'missing_scope':
                print(f"❌ Error sending formatted message: {error_msg}", file=sys.stderr)
                print(f"💡 Your token needs 'chat:write' scope to send messages", file=sys.stderr)
            elif error_msg == 'channel_not_found':
                print(f"❌ Channel {target_channel} not found or bot doesn't have access", file=sys.stderr)
            elif error_msg == 'not_in_channel':
                print(f"❌ GESBot is not a member of {target_channel}", file=sys.stderr)
                print(f"💡 Add GESBot to the channel first: /invite @GESBot", file=sys.stderr)
            else:
                print(f"❌ Error sending formatted message: {error_msg}", file=sys.stderr)
            return None


def translate_markdown_for_slack(text):
    """
    Translate standard markdown to Slack's markdown format and handle tables.
    """
    import re
    
    # Convert double asterisk bold to single asterisk
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
    
    # Handle markdown tables
    lines = text.split('\n')
    result_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Detect markdown table start (line with | characters)
        if '|' in line and line.strip().startswith('|') and line.strip().endswith('|'):
            table_lines = []
            table_start = i
            
            # Collect all table lines
            while i < len(lines) and '|' in lines[i] and lines[i].strip().startswith('|'):
                current_line = lines[i].strip()
                
                # Skip separator lines (ones with dashes)
                if not re.match(r'^\|[\s\-|:]+\|$', current_line):
                    table_lines.append(current_line)
                
                i += 1
            
            # Convert table to formatted text block
            if table_lines:
                formatted_table = format_table_for_slack(table_lines)
                result_lines.append('```')
                result_lines.extend(formatted_table)
                result_lines.append('```')
            
            # Don't increment i here since it's already advanced
            continue
        else:
            result_lines.append(line)
            i += 1
    
    return '\n'.join(result_lines)


def format_table_for_slack(table_lines):
    """
    Format markdown table lines for Slack code block display.
    """
    if not table_lines:
        return []
    
    # Parse table data
    rows = []
    for line in table_lines:
        # Split on | and clean up
        cells = [cell.strip() for cell in line.split('|')[1:-1]]  # Remove empty first/last
        rows.append(cells)
    
    if not rows:
        return []
    
    # Calculate column widths
    num_cols = len(rows[0])
    col_widths = [0] * num_cols
    
    for row in rows:
        for i, cell in enumerate(row):
            if i < num_cols:
                # Remove markdown formatting for width calculation
                clean_cell = cell.replace('*', '')
                col_widths[i] = max(col_widths[i], len(clean_cell))
    
    # Format rows with proper spacing
    formatted_rows = []
    for row_idx, row in enumerate(rows):
        formatted_cells = []
        for i, cell in enumerate(row):
            if i < num_cols:
                # Remove markdown asterisks for display
                display_cell = cell.replace('*', '')
                # Pad to column width
                padded_cell = display_cell.ljust(col_widths[i])
                formatted_cells.append(padded_cell)
        
        formatted_row = ' | '.join(formatted_cells)
        formatted_rows.append(formatted_row)
        
        # Add separator line after header (first row)
        if row_idx == 0 and len(rows) > 1:
            separator_cells = ['-' * col_widths[i] for i in range(num_cols)]
            separator_row = '-|-'.join(separator_cells)
            formatted_rows.append(separator_row)
    
    return formatted_rows


def main():
    """Pipeline-friendly main function that reads stdin and sends to Slack."""
    
    parser = argparse.ArgumentParser(description='Send messages to Slack via pipeline')
    parser.add_argument('destination', nargs='?', help='Slack channel or user (e.g., #channel, @user)')
    parser.add_argument('--text-only', action='store_true', help='Send as plain text instead of blocks')
    
    args = parser.parse_args()
    
    # Read input from stdin
    if sys.stdin.isatty():
        print("Error: No input provided. This script expects input via pipeline.", file=sys.stderr)
        print("Usage: echo 'message' | python slackbot.py [destination]", file=sys.stderr)
        sys.exit(1)
    
    input_data = sys.stdin.read().strip()
    
    if not input_data:
        print("Error: Empty input received", file=sys.stderr)
        sys.exit(1)
    
    # Create bot instance
    bot = SlackBot()
    
    # Try to parse as JSON first (for block messages), fallback to plain text
    try:
        if not args.text_only:
            message_data = json.loads(input_data)
            
            if isinstance(message_data, dict):
                # Handle structured message with blocks
                if 'blocks' in message_data:
                    response = bot.send_message_with_blocks(
                        blocks=message_data['blocks'],
                        text=message_data.get('text', ''),
                        channel=args.destination
                    )
                elif 'text' in message_data:
                    response = bot.send_message(
                        text=message_data['text'],
                        channel=args.destination
                    )
                else:
                    print("Error: Invalid message structure", file=sys.stderr)
                    sys.exit(1)
            else:
                print("Error: Message data must be a dictionary", file=sys.stderr)
                sys.exit(1)
        else:
            # Force plain text mode
            raise json.JSONDecodeError("", "", 0)
            
    except json.JSONDecodeError:
        # Send as plain text, translating markdown for Slack
        slack_formatted_text = translate_markdown_for_slack(input_data)
        response = bot.send_message(
            text=slack_formatted_text,
            channel=args.destination
        )
    
    if not response:
        sys.exit(1)


if __name__ == "__main__":
    main()
