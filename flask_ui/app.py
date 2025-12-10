from flask import Flask, render_template, jsonify
import json
import os
from datetime import datetime
import pytz

app = Flask(__name__)

# Pointing to the log file in the container
LOG_FILE = '/app/logs/cowrie.json'
IST = pytz.timezone('Asia/Kolkata')

def parse_logs():
    data = []
    if not os.path.exists(LOG_FILE):
        return []

    try:
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
    except Exception:
        return []
        
    # Process newest first
    for line in reversed(lines):
        try:
            entry = json.loads(line)
            event_id = entry.get('eventid')
            
            # Filter for commands and login attempts
            if event_id not in ['cowrie.command.input', 'cowrie.login.success', 'cowrie.login.failed']:
                continue

            # Timestamp parsing and conversion
            timestamp_str = entry.get('timestamp')
            ts_display = "N/A"
            if timestamp_str:
                try:
                    # Replace Z with +0000 for standard parsing if needed, though %z handles it usually if compliant
                    # Cowrie uses ...Z usually.
                    if timestamp_str.endswith('Z'):
                        timestamp_str = timestamp_str[:-1] + '+0000'
                    
                    dt_utc = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%f%z')
                    dt_ist = dt_utc.astimezone(IST)
                    ts_display = dt_ist.strftime('%I:%M:%S %p')
                except ValueError:
                    ts_display = timestamp_str

            ip = entry.get('src_ip', 'Unknown')
            
            item = {
                'timestamp': ts_display,
                'ip': ip,
                'message': '',
                'class': 'text-muted'
            }

            if event_id == 'cowrie.command.input':
                cmd = entry.get('input', '')
                item['message'] = f"{cmd}"
                
                # Simple heuristic: Common supported commands = Green, Others (likely typos/unsupported) = Orange
                # Split to get just the first word (the command)
                cmd_base = cmd.strip().split()[0] if cmd.strip() else ""
                common_cmds = [
                    'ls', 'll', 'la', 'cd', 'pwd', 'mkdir', 'rmdir', 'rm', 'mv', 'cp',
                    'cat', 'more', 'less', 'head', 'tail', 'grep', 'find',
                    'echo', 'history', 'clear', 'exit', 'quit',
                    'whoami', 'id', 'uname', 'hostname',
                    'ps', 'top', 'df', 'du', 'free',
                    'netstat', 'ip', 'ifconfig',
                    'ping', 'traceroute', 'wget', 'curl',
                    'ssh', 'scp', 'sftp',
                    'apt', 'apt-get', 'yum', 'dnf', 'dpkg',
                    'tar', 'gzip', 'gunzip', 'unzip', 'zip',
                    'passwd', 'sudo', 'su',
                    'touch', 'chmod', 'chown'
                ]
                
                if cmd_base in common_cmds:
                    item['class'] = 'success-row'
                else:
                    item['class'] = 'warning-row' # Orange for unknown/typos

            elif event_id == 'cowrie.login.success':
                user = entry.get('username', '')
                pwd = entry.get('password', '')
                item['message'] = f"LOGIN SUCCESS: {user} / {pwd}"
                item['class'] = 'success-row'
            elif event_id == 'cowrie.login.failed':
                user = entry.get('username', '')
                pwd = entry.get('password', '')
                item['message'] = f"LOGIN FAILED: {user} / {pwd}"
                item['class'] = 'failed-row'

            data.append(item)
        except Exception:
            continue
            
    return data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def get_data():
    return jsonify(parse_logs())

print("Starting Flask App...")
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
