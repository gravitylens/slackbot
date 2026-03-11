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
    Translate standard markdown to Slack's markdown format and detect tables.
    Returns tuple: (processed_text, has_tables, table_data)
    """
    import re
    
    # Convert double asterisk bold to single asterisk
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
    
    # Handle markdown tables
    lines = text.split('\n')
    result_lines = []
    tables_found = []
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
            
            # Store table data for block conversion
            if table_lines:
                tables_found.append(table_lines)
                result_lines.append(f'__TABLE_PLACEHOLDER_{len(tables_found)-1}__')
            
            # Don't increment i here since it's already advanced
            continue
        else:
            result_lines.append(line)
            i += 1
    
    processed_text = '\n'.join(result_lines)
    has_tables = len(tables_found) > 0
    
    return processed_text, has_tables, tables_found


def format_table_for_slack(table_lines):
    """
    Format markdown table lines for Slack code block display.
    Handles long text by limiting column widths.
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
    
    # Calculate column widths with maximum limits to prevent overly wide tables
    num_cols = len(rows[0])
    col_widths = [0] * num_cols
    max_col_width = 40  # Limit column width for readability
    
    for row in rows:
        for i, cell in enumerate(row):
            if i < num_cols:
                # Remove markdown formatting for width calculation
                clean_cell = cell.replace('*', '')
                # Limit individual column width
                display_width = min(len(clean_cell), max_col_width)
                col_widths[i] = max(col_widths[i], display_width)
    
    # Format rows with proper spacing and text wrapping
    formatted_rows = []
    for row_idx, row in enumerate(rows):
        formatted_cells = []
        for i, cell in enumerate(row):
            if i < num_cols:
                # Remove markdown asterisks for display
                display_cell = cell.replace('*', '')
                
                # Truncate long text with ellipsis
                if len(display_cell) > max_col_width:
                    display_cell = display_cell[:max_col_width-3] + "..."
                
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


def create_table_blocks(tables_found):
    """
    Convert parsed table data into Slack block format.
    For large tables, consolidate rows to stay within Slack's 50 block limit.
    """
    blocks = []
    
    for table_lines in tables_found:
        if not table_lines:
            continue
        
        # Parse table data
        rows = []
        for line in table_lines:
            # Split on | and clean up
            cells = [cell.strip() for cell in line.split('|')[1:-1]]  # Remove empty first/last
            rows.append(cells)
        
        if not rows:
            continue
        
        # Create table header if available
        if len(rows) > 0:
            header_row = rows[0]
            header_text = " | ".join([f"*{cell}*" for cell in header_row])
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": header_text
                }
            })
            
            # Add divider after header
            if len(rows) > 1:
                blocks.append({
                    "type": "divider"
                })
        
        # Handle data rows - consolidate if table is large
        data_rows = rows[1:]  # Skip header row
        if len(data_rows) > 40:  # If too many rows, consolidate
            # Group rows together to stay under block limit
            rows_per_block = max(2, len(data_rows) // 20)  # Aim for ~20 blocks max
            
            for i in range(0, len(data_rows), rows_per_block):
                chunk = data_rows[i:i + rows_per_block]
                combined_text = []
                
                for row in chunk:
                    if row:
                        row_text = " | ".join(row)
                        combined_text.append(row_text)
                
                if combined_text:
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "\n".join(combined_text)
                        }
                    })
        else:
            # Small table - use one block per row
            for row in data_rows:
                if row:
                    row_text = " | ".join(row)
                    blocks.append({
                        "type": "section", 
                        "text": {
                            "type": "mrkdwn",
                            "text": row_text
                        }
                    })
        
        # Add spacing between tables if multiple tables
        if len(tables_found) > 1:
            blocks.append({
                "type": "divider"
            })
    
    return blocks


def create_message_with_tables(text, tables_found):
    """
    Create a complete Slack message with blocks that include tables.
    """
    blocks = []
    
    # Process text and tables in order
    if '__TABLE_PLACEHOLDER' in text:
        text_parts = []
        current_text = text
        
        # Split text around table placeholders
        for i in range(len(tables_found)):
            placeholder = f'__TABLE_PLACEHOLDER_{i}__'
            if placeholder in current_text:
                parts = current_text.split(placeholder, 1)
                text_parts.append(parts[0])
                current_text = parts[1] if len(parts) > 1 else ""
        
        # Add remaining text after last table
        text_parts.append(current_text)
        
        # Build blocks alternating between text and tables
        for i in range(len(tables_found)):
            # Add text before this table
            if text_parts[i].strip():
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn", 
                        "text": text_parts[i].strip()
                    }
                })
            
            # Add table blocks
            table_blocks = create_table_blocks([tables_found[i]])
            blocks.extend(table_blocks)
        
        # Add text after last table
        if len(text_parts) > len(tables_found) and text_parts[-1].strip():
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text_parts[-1].strip()
                }
            })
    else:
        # No tables, just add text
        if text.strip():
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text.strip()
                }
            })
    
    return blocks


def format_table_for_csv(table_lines, separator='\t'):
    """
    Format markdown table lines for spreadsheet-friendly CSV/TSV output.
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
    
    # Format rows with chosen separator (tab for TSV, comma for CSV)
    formatted_rows = []
    for row in rows:
        # Clean up cells - remove markdown formatting and escape quotes for CSV
        clean_cells = []
        for cell in row:
            # Remove markdown asterisks
            clean_cell = cell.replace('*', '')
            
            # For CSV, escape quotes and wrap fields with commas in quotes
            if separator == ',':
                if ',' in clean_cell or '"' in clean_cell:
                    clean_cell = '"' + clean_cell.replace('"', '""') + '"'
            
            clean_cells.append(clean_cell)
        
        formatted_row = separator.join(clean_cells)
        formatted_rows.append(formatted_row)
    
    return formatted_rows


def main():
    """Pipeline-friendly main function that reads stdin and sends to Slack."""
    
    parser = argparse.ArgumentParser(description='Send messages to Slack via pipeline')
    parser.add_argument('destination', nargs='?', help='Slack channel or user (e.g., #channel, @user)')
    parser.add_argument('--text-only', action='store_true', help='Send as plain text instead of blocks')
    parser.add_argument('--csv', action='store_true', help='Format tables as comma-separated values (spreadsheet friendly)')
    parser.add_argument('--tsv', action='store_true', help='Format tables as tab-separated values (spreadsheet friendly)')
    
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
        # Process markdown and detect tables
        processed_text, has_tables, tables_found = translate_markdown_for_slack(input_data)
        
        if has_tables and not (args.text_only or args.csv or args.tsv):
            # Create block message with tables
            blocks = create_message_with_tables(processed_text, tables_found)
            response = bot.send_message_with_blocks(
                blocks=blocks,
                text=f"Message with {len(tables_found)} table(s)",
                channel=args.destination
            )
        else:
            # Send as regular text (fallback, text-only, CSV, or TSV mode)
            if has_tables and (args.csv or args.tsv):
                # Format tables as CSV/TSV for spreadsheet copying
                formatted_parts = []
                current_text = processed_text
                separator = ',' if args.csv else '\t'
                
                # Process text and tables in order
                for i in range(len(tables_found)):
                    placeholder = f'__TABLE_PLACEHOLDER_{i}__'
                    if placeholder in current_text:
                        parts = current_text.split(placeholder, 1)
                        
                        # Add text before table
                        if parts[0].strip():
                            formatted_parts.append(parts[0].strip())
                        
                        # Add CSV/TSV formatted table
                        if tables_found[i]:
                            formatted_table = format_table_for_csv(tables_found[i], separator)
                            formatted_parts.extend(formatted_table)
                        
                        # Continue with remaining text
                        current_text = parts[1] if len(parts) > 1 else ""
                
                # Add any remaining text
                if current_text.strip():
                    formatted_parts.append(current_text.strip())
                
                final_text = '\n'.join(formatted_parts)
            elif args.text_only and has_tables:
                formatted_parts = []
                current_text = processed_text
                
                # Process text and tables in order
                for i in range(len(tables_found)):
                    placeholder = f'__TABLE_PLACEHOLDER_{i}__'
                    if placeholder in current_text:
                        parts = current_text.split(placeholder, 1)
                        
                        # Add text before table
                        if parts[0].strip():
                            formatted_parts.append(parts[0].strip())
                        
                        # Add formatted table
                        if tables_found[i]:
                            formatted_table = format_table_for_slack(tables_found[i])
                            formatted_parts.extend(['```'] + formatted_table + ['```'])
                        
                        # Continue with remaining text
                        current_text = parts[1] if len(parts) > 1 else ""
                
                # Add any remaining text
                if current_text.strip():
                    formatted_parts.append(current_text.strip())
                
                final_text = '\n'.join(formatted_parts)
            else:
                # Remove table placeholders for regular text mode
                final_text = processed_text
                for i in range(len(tables_found)):
                    placeholder = f'__TABLE_PLACEHOLDER_{i}__'
                    final_text = final_text.replace(placeholder, '')
                
                # Clean up extra whitespace
                final_text = '\n'.join(line for line in final_text.split('\n') if line.strip())
            
            response = bot.send_message(
                text=final_text,
                channel=args.destination
            )
    
    if not response:
        sys.exit(1)


if __name__ == "__main__":
    main()
