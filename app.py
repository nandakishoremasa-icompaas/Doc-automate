import os
import sys
import time
import queue
import threading
import subprocess
from flask import Flask, render_template, request, Response, jsonify

app = Flask(__name__)

collate_process = None
subscribers = []
log_history = []
process_lock = threading.Lock()
current_status = "IDLE"  # IDLE, RUNNING, COMPLETED, ABORTED, FAILED
current_source_url = ""
current_target_url = ""

def broadcast_log(line):
    # Strip newline characters for clean storage/sending
    clean_line = line.rstrip('\r\n')
    log_history.append(clean_line)
    for q in list(subscribers):
        try:
            q.put(clean_line)
        except Exception:
            pass

def read_stdout(process):
    global current_status, collate_process
    # Read stdout line-by-line and stream it
    for line in iter(process.stdout.readline, ''):
        broadcast_log(line)
    process.stdout.close()
    
    return_code = process.wait()
    with process_lock:
        if current_status == "RUNNING":
            if return_code == 0:
                current_status = "COMPLETED"
                broadcast_log("🎉 ALL OPERATIONS COMPLETED SUCCESSFULLY!")
            else:
                current_status = "FAILED"
                broadcast_log(f"❌ PROCESS TERMINATED WITH ERROR (Exit Code: {return_code})")
        collate_process = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/status')
def get_status():
    return jsonify({
        "status": current_status,
        "sourceUrl": current_source_url,
        "targetUrl": current_target_url
    })

@app.route('/start', methods=['POST'])
def start():
    global collate_process, current_status, log_history, current_source_url, current_target_url
    source_url = request.form.get('sourceUrl', '').strip()
    target_url = request.form.get('targetUrl', '').strip()
    
    if not source_url or not target_url:
        return jsonify({"error": "Both Source Folder and Target Document URLs are required."}), 400
        
    with process_lock:
        if collate_process and collate_process.poll() is None:
            return jsonify({"error": "Automation is already running."}), 400
            
        log_history.clear()
        current_source_url = source_url
        current_target_url = target_url
        current_status = "RUNNING"
        
        broadcast_log("🚀 Initializing Collation Pipeline...")
        broadcast_log(f"📂 Source: {source_url}")
        broadcast_log(f"📄 Target: {target_url}")
        
        try:
            # We run python in unbuffered mode (-u) so we get logs in real time
            cmd = ["./venv/bin/python3", "-u", "collate_policies.py", "--source", source_url, "--target", target_url]
            if request.form.get('visible') == 'true':
                cmd.append('--visible')
                
            collate_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Start background stdout reader thread
            threading.Thread(target=read_stdout, args=(collate_process,), daemon=True).start()
            return jsonify({"status": "started"}), 200
        except Exception as e:
            current_status = "FAILED"
            broadcast_log(f"❌ Failed to spawn automation script: {e}")
            return jsonify({"error": str(e)}), 500

@app.route('/verify', methods=['POST'])
def verify():
    global collate_process, current_status, log_history, current_source_url, current_target_url
    source_url = request.form.get('sourceUrl', '').strip()
    target_url = request.form.get('targetUrl', '').strip()
    
    if not source_url or not target_url:
        return jsonify({"error": "Both Source Folder and Target Document URLs are required for verification."}), 400
        
    with process_lock:
        if collate_process and collate_process.poll() is None:
            return jsonify({"error": "Automation is already running."}), 400
            
        log_history.clear()
        current_source_url = source_url
        current_target_url = target_url
        current_status = "RUNNING"
        
        broadcast_log("🔍 Initializing Standalone Verification & Healing...")
        broadcast_log(f"📂 Source: {source_url}")
        broadcast_log(f"📄 Target: {target_url}")
        
        try:
            cmd = ["./venv/bin/python3", "-u", "collate_policies.py", "--source", source_url, "--target", target_url, "--verify-only"]
            if request.form.get('visible') == 'true':
                cmd.append('--visible')
                
            collate_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            threading.Thread(target=read_stdout, args=(collate_process,), daemon=True).start()
            return jsonify({"status": "started"}), 200
        except Exception as e:
            current_status = "FAILED"
            broadcast_log(f"❌ Failed to spawn automation script: {e}")
            return jsonify({"error": str(e)}), 500

@app.route('/stop', methods=['POST'])
def stop():
    global collate_process, current_status
    with process_lock:
        if collate_process and collate_process.poll() is None:
            broadcast_log("⚠️ Stop request received. Terminating collation process...")
            collate_process.terminate()
            try:
                collate_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                collate_process.kill()
            collate_process = None
            current_status = "ABORTED"
            broadcast_log("🛑 Process terminated by user.")
            return jsonify({"status": "stopped"}), 200
        else:
            return jsonify({"error": "No running process found."}), 400

@app.route('/stream')
def stream():
    def event_generator():
        # First send logs history
        for line in log_history:
            yield f"data: {line}\n\n"
            
        # Register new queue for active streaming
        q = queue.Queue()
        subscribers.append(q)
        try:
            while True:
                line = q.get()
                yield f"data: {line}\n\n"
        except GeneratorExit:
            pass
        finally:
            subscribers.remove(q)
            
    return Response(event_generator(), mimetype="text/event-stream")

if __name__ == '__main__':
    # Listen on port 5000 of all interfaces
    app.run(host='0.0.0.0', port=5000, debug=False)
