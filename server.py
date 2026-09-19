#!/usr/bin/env python3
import http.server
import socketserver
import urllib.parse
import urllib.request
import json
import os
import sys
import re
import uuid
import time
import socket
import queue
import threading

# Admin Authentication Security
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "selecto@admin2026")
ADMIN_TOKENS = set()

def create_admin_token():
    token = uuid.uuid4().hex + uuid.uuid4().hex
    ADMIN_TOKENS.add(token)
    return token

def verify_admin_token(token):
    return token and token in ADMIN_TOKENS

PORT = int(os.environ.get("PORT", 8080))
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
# On Render, use /data for persistent storage; locally use app directory
_DATA_DIR = "/data" if os.path.isdir("/data") else DIRECTORY
DATA_FILE = os.path.join(_DATA_DIR, "sessions.json")
ANALYTICS_FILE = os.path.join(_DATA_DIR, "analytics.json")
USERS_FILE = os.path.join(_DATA_DIR, "users.json")

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_users(users):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Users Storage Error] {e}")

def is_user_active(user_data):
    if not user_data:
        return False
    status = user_data.get('status', 'pending_payment')
    if status != 'active':
        return False
    expires_at = user_data.get('expires_at', '')
    if expires_at:
        try:
            exp_time = time.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
            if time.time() > time.mktime(exp_time):
                return False
        except Exception:
            pass
    return True


def load_analytics():
    if os.path.exists(ANALYTICS_FILE):
        try:
            with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"total_views": 0, "unique_ips": [], "last_visit": ""}

def record_visit(ip):
    try:
        data = load_analytics()
        data["total_views"] = data.get("total_views", 0) + 1
        ips = set(data.get("unique_ips", []))
        if ip:
            ips.add(ip)
        data["unique_ips"] = list(ips)
        data["last_visit"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Analytics Error] {e}")

# Google Drive API Key for reliable folder listing
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyBZeLlQvFy8XIUmnrErc5cP8jDpSx6DHy0")

IMAGE_EXTENSIONS = (
    '.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', 
    '.gif', '.bmp', '.tiff', '.tif', '.raw', '.cr2', 
    '.nef', '.arw', '.dng', '.svg'
)

def get_local_ip():
    """Try multiple methods to get the real LAN IP."""
    # Method 1: connect to external host (most reliable)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    # Method 2: hostname resolution
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    # Method 3: scan network interfaces
    try:
        import subprocess
        result = subprocess.check_output(
            ["ipconfig", "getifaddr", "en0"], timeout=2
        ).decode().strip()
        if result:
            return result
    except Exception:
        pass
    try:
        import subprocess
        result = subprocess.check_output(
            ["ipconfig", "getifaddr", "en1"], timeout=2
        ).decode().strip()
        if result:
            return result
    except Exception:
        pass
    return "127.0.0.1"

LOCAL_IP = get_local_ip()

# In-Memory Real-time Session Subscribers for Sub-30ms SSE broadcast
# session_id -> list of queue.Queue
SESSION_SUBSCRIBERS = {}
SESSION_LOCK = threading.Lock()

def broadcast_session_event(session_id, event_data):
    with SESSION_LOCK:
        if session_id in SESSION_SUBSCRIBERS:
            dead_queues = []
            for q in SESSION_SUBSCRIBERS[session_id]:
                try:
                    q.put_nowait(event_data)
                except Exception:
                    dead_queues.append(q)
            for dq in dead_queues:
                SESSION_SUBSCRIBERS[session_id].remove(dq)

def get_subscriber_count(session_id):
    with SESSION_LOCK:
        return len(SESSION_SUBSCRIBERS.get(session_id, []))

def load_sessions():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_sessions(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Storage Error] {e}")

def is_image_file(filename):
    if not filename:
        return True
    ext = os.path.splitext(filename.lower())[1]
    if not ext:
        return True
    return ext in IMAGE_EXTENSIONS

def clean_folder_id(url_or_id):
    if not url_or_id:
        return ""
    text = urllib.parse.unquote(url_or_id.strip())
    m = re.search(r'folders\/([a-zA-Z0-9_-]+)', text)
    if m:
        return m.group(1).split('?')[0]
    m2 = re.search(r'id=([a-zA-Z0-9_-]+)', text)
    if m2:
        return m2.group(1).split('&')[0]
    m3 = re.search(r'file\/d\/([a-zA-Z0-9_-]+)', text)
    if m3:
        return m3.group(1).split('?')[0]
    m4 = re.search(r'([a-zA-Z0-9_-]{25,50})', text)
    if m4:
        return m4.group(1)
    return text.split('?')[0].split('&')[0]

class PhotoProofingHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def get_network_url(self, session_id):
        """Build correct share URL using request Host header IP (real LAN IP)."""
        try:
            host_header = self.headers.get('Host', '')
            # Host header has the real IP:port that the client used to connect
            if host_header and not host_header.startswith('127.') and not host_header.startswith('localhost'):
                return f"http://{host_header}/?session={session_id}"
        except Exception:
            pass
        # Fallback to detected LOCAL_IP
        return f"http://{LOCAL_IP}:{PORT}/?session={session_id}"

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)

        # Record visit analytics for page requests
        if parsed.path in ('/', '/admin', '/admin/'):
            client_ip = self.headers.get('X-Forwarded-For', self.client_address[0]).split(',')[0].strip()
            record_visit(client_ip)

        # Admin Dashboard HTML route
        if parsed.path in ('/admin', '/admin/'):
            self.handle_admin_dashboard(parsed.query)
            return

        # Admin Stats API route
        if parsed.path == '/api/admin/stats':
            self.handle_admin_stats()
            return
        
        # 1. Real-Time SSE Stream for Zero-Lag Live Co-Viewing (< 30ms)
        if parsed.path == '/api/session/stream':
            self.handle_session_stream(parsed.query)
            return

        # 2. Folder extractor API
        if parsed.path == '/api/folder':
            self.handle_api_folder(parsed.query)
            return

        # 3. Session fetch API
        if parsed.path == '/api/session':
            self.handle_get_session(parsed.query)
            return

        # 4. Proxy image for CORS-safe Watermark Canvas rendering
        if parsed.path == '/api/proxy-image':
            self.handle_proxy_image(parsed.query)
            return

        # 5. Network info API
        if parsed.path == '/api/network-info':
            self.send_json_response(200, {
                "localIp": LOCAL_IP,
                "port": PORT,
                "networkUrl": f"http://{LOCAL_IP}:{PORT}"
            })
            return

        # 6. Export Organized 3-Folder ZIP
        if parsed.path == '/api/session/export-zip':
            self.handle_export_zip(parsed.query)
            return

        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len) if content_len > 0 else b'{}'
        
        try:
            payload = json.loads(post_body.decode('utf-8'))
        except Exception:
            payload = {}

        if parsed.path == '/api/auth/google-login':
            self.handle_google_login(payload)
            return

        if parsed.path == '/api/auth/user-profile':
            self.handle_user_profile(payload)
            return

        if parsed.path == '/api/payment/activate':
            self.handle_payment_activate(payload)
            return

        if parsed.path == '/api/admin/user-action':
            self.handle_admin_user_action(payload)
            return

        if parsed.path == '/api/admin/login':
            self.handle_admin_login(payload)
            return

        if parsed.path == '/api/admin/logout':
            self.handle_admin_logout()
            return

        if parsed.path == '/api/session/create':
            self.handle_create_session(payload)
            return
        elif parsed.path == '/api/session/navigate':
            self.handle_session_navigate(payload)
            return
        elif parsed.path == '/api/session/vote':
            self.handle_session_vote(payload)
            return
        elif parsed.path == '/api/session/settings':
            self.handle_session_settings(payload)
            return
        elif parsed.path == '/api/drive/sync-folders':
            self.handle_drive_folder_sync(payload)
            return

        self.send_json_response(404, {"error": "Endpoint not found"})

    # --- REAL-TIME SERVER-SENT EVENTS (SSE) STREAM (< 30ms ZERO LAG) ---
    def handle_session_stream(self, query_string):
        params = urllib.parse.parse_qs(query_string)
        session_id = params.get('id', [''])[0]
        client_role = params.get('role', ['client'])[0]

        if not session_id:
            self.send_error(400, "Session ID required")
            return

        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        msg_queue = queue.Queue()
        with SESSION_LOCK:
            if session_id not in SESSION_SUBSCRIBERS:
                SESSION_SUBSCRIBERS[session_id] = []
            SESSION_SUBSCRIBERS[session_id].append(msg_queue)

        # Notify viewers count update
        viewers = get_subscriber_count(session_id)
        broadcast_session_event(session_id, {
            "type": "PRESENCE",
            "viewers": viewers
        })

        # Send initial ping
        try:
            self.wfile.write(f"data: {json.dumps({'type': 'CONNECTED', 'viewers': viewers})}\n\n".encode('utf-8'))
            self.wfile.flush()

            while True:
                try:
                    # Wait for broadcasted events
                    event = msg_queue.get(timeout=25.0)
                    msg = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    self.wfile.write(msg.encode('utf-8'))
                    self.wfile.flush()
                except queue.Empty:
                    # Keep-alive heartbeat ping every 25s
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            with SESSION_LOCK:
                if session_id in SESSION_SUBSCRIBERS and msg_queue in SESSION_SUBSCRIBERS[session_id]:
                    SESSION_SUBSCRIBERS[session_id].remove(msg_queue)
            broadcast_session_event(session_id, {
                "type": "PRESENCE",
                "viewers": get_subscriber_count(session_id)
            })

    # --- INSTANT NAVIGATION BROADCAST (< 30ms) ---
    def handle_session_navigate(self, payload):
        session_id = payload.get('sessionId')
        photo_index = payload.get('photoIndex', 0)
        photo_id = payload.get('photoId', '')
        preview_url = payload.get('previewUrl', '')
        thumb_url = payload.get('thumbUrl', '')
        url = payload.get('url', '')
        sender = payload.get('sender', 'user')

        if not session_id:
            self.send_json_response(400, {"success": False, "error": "Session ID required"})
            return

        # Update last active index in session
        sessions = load_sessions()
        if session_id in sessions:
            sessions[session_id]['lastActiveIndex'] = photo_index
            sessions[session_id]['lastActivePhotoId'] = photo_id
            save_sessions(sessions)

        # Broadcast INSTANTLY to client / photographer screens with dual-resolution preview!
        broadcast_session_event(session_id, {
            "type": "NAVIGATE",
            "photoIndex": photo_index,
            "photoId": photo_id,
            "previewUrl": preview_url,
            "thumbUrl": thumb_url,
            "url": url,
            "sender": sender,
            "timestamp": time.time()
        })

        self.send_json_response(200, {"success": True, "photoIndex": photo_index})

    # --- EXPORT ORGANIZED 3-FOLDERS ZIP (SELECTED / REJECTED / DECIDE) ---
    def handle_export_zip(self, query_string):
        import zipfile
        import io

        params = urllib.parse.parse_qs(query_string)
        session_id = params.get('id', [''])[0]
        sessions = load_sessions()

        if not session_id or session_id not in sessions:
            self.send_json_response(404, {"error": "Session not found"})
            return

        session = sessions[session_id]
        photos = session.get('photos', [])
        decisions = session.get('decisions', {})
        title = session.get('title', 'Event_Photos').replace(' ', '_')

        selected = [p for p in photos if decisions.get(p.get('id')) == 'select']
        rejected = [p for p in photos if decisions.get(p.get('id')) == 'reject']
        decide = [p for p in photos if decisions.get(p.get('id')) == 'maybe']

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 1. Selected Photos Folder
            sel_text = "\n".join([f"{p.get('title', p.get('id'))} - {p.get('downloadUrl', p.get('url'))}" for p in selected])
            zf.writestr("Selected_Photos/Selected_List.txt", sel_text or "No photos selected yet.")
            
            sel_csv = "Index,Filename,PhotoID,DriveURL\n"
            for i, p in enumerate(selected, 1):
                sel_csv += f"{i},\"{p.get('title', '')}\",\"{p.get('id', '')}\",\"{p.get('downloadUrl', p.get('url'))}\"\n"
            zf.writestr("Selected_Photos/Selected_Manifest.csv", sel_csv)

            # 2. Rejected Photos Folder
            rej_text = "\n".join([f"{p.get('title', p.get('id'))} - {p.get('downloadUrl', p.get('url'))}" for p in rejected])
            zf.writestr("Rejected_Photos/Rejected_List.txt", rej_text or "No photos rejected.")

            # 3. Decide Later Photos Folder
            dec_text = "\n".join([f"{p.get('title', p.get('id'))} - {p.get('downloadUrl', p.get('url'))}" for p in decide])
            zf.writestr("Decide_Later/Decide_Later_List.txt", dec_text or "No photos marked for decide later.")

            # 4. Lightroom Search Filter
            lr_filenames = [p.get('title', '') for p in selected if p.get('title')]
            lr_clean = [os.path.splitext(f)[0] for f in lr_filenames]
            lr_query = " ".join(lr_clean)
            zf.writestr("Lightroom_Filter_Search.txt", lr_query or "No selections yet.")

            # 5. Summary
            summary = f"""selecto - Selection Summary
Tagline: Photo Selection, Simplified.
Event: {session.get('title', 'Event')}
Total Photos: {len(photos)}
Selected (Green): {len(selected)}
Rejected (Red): {len(rejected)}
Decide Later (Yellow): {len(decide)}

How to use:
1. Adobe Lightroom: Open Lightroom_Filter_Search.txt, copy all text, and paste into Library Filter > Text > Filename contains.
2. Google Drive: Use Selected_Manifest.csv to batch move selected photos into your client folder.
"""
            zf.writestr("README_Selection_Summary.txt", summary)

        zip_data = zip_buffer.getvalue()
        self.send_response(200)
        self.send_header('Content-Type', 'application/zip')
        self.send_header('Content-Disposition', f'attachment; filename="selecto_{title}_Organized.zip"')
        self.send_header('Content-Length', str(len(zip_data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(zip_data)

    # --- INSTANT DECISION BROADCAST (SELECT / REJECT / DECIDE) ---
    def handle_session_vote(self, payload):
        session_id = payload.get('sessionId')
        photo_id = payload.get('photoId')
        decision = payload.get('decision') # 'select', 'reject', 'maybe', 'none'
        sender = payload.get('sender', 'user')

        if not session_id or not photo_id:
            self.send_json_response(400, {"success": False, "error": "Session ID and Photo ID required."})
            return

        sessions = load_sessions()
        if session_id not in sessions:
            self.send_json_response(404, {"success": False, "error": "Session not found."})
            return

        if decision == 'none' or not decision:
            sessions[session_id]['decisions'].pop(photo_id, None)
        else:
            sessions[session_id]['decisions'][photo_id] = decision

        save_sessions(sessions)

        decisions = sessions[session_id]['decisions']
        selected_count = sum(1 for v in decisions.values() if v == 'select')
        rejected_count = sum(1 for v in decisions.values() if v == 'reject')
        maybe_count = sum(1 for v in decisions.values() if v == 'maybe')
        total = len(sessions[session_id].get('photos', []))

        stats = {
            "selected": selected_count,
            "rejected": rejected_count,
            "maybe": maybe_count,
            "undecided": max(0, total - (selected_count + rejected_count + maybe_count)),
            "total": total
        }

        # Broadcast vote INSTANTLY to all connected client & photographer screens!
        broadcast_session_event(session_id, {
            "type": "VOTE",
            "photoId": photo_id,
            "decision": decision,
            "sender": sender,
            "stats": stats,
            "timestamp": time.time()
        })

        # If Google Drive bridge webhook is configured, asynchronously call it
        bridge_url = sessions[session_id].get('driveBridgeUrl')
        folder_url = sessions[session_id].get('folderUrl', '')
        if bridge_url and decision in ('select', 'reject', 'maybe'):
            threading.Thread(target=self._trigger_drive_bridge, args=(bridge_url, folder_url, photo_id, decision)).start()

        self.send_json_response(200, {
            "success": True,
            "photoId": photo_id,
            "decision": decision,
            "stats": stats
        })

    def _trigger_drive_bridge(self, bridge_url, folder_url, photo_id, decision):
        try:
            folder_id = clean_folder_id(folder_url)
            req_data = json.dumps({
                "action": "organize",
                "folderId": folder_id,
                "photoId": photo_id,
                "decision": decision
            }).encode('utf-8')
            req = urllib.request.Request(bridge_url, data=req_data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                print(f"[Drive Bridge] Organized photo {photo_id} into {decision}: status {resp.status}")
        except Exception as e:
            print(f"[Drive Bridge Error] {e}")

    # --- GOOGLE DRIVE 3-FOLDER SYNC / SETUP ---
    def handle_drive_folder_sync(self, payload):
        session_id = payload.get('sessionId')
        bridge_url = payload.get('bridgeUrl')
        folder_url = payload.get('folderUrl')

        if not session_id:
            self.send_json_response(400, {"success": False, "error": "Session ID required"})
            return

        sessions = load_sessions()
        if session_id not in sessions:
            self.send_json_response(404, {"success": False, "error": "Session not found"})
            return

        if bridge_url:
            sessions[session_id]['driveBridgeUrl'] = bridge_url
            save_sessions(sessions)

        folder_id = clean_folder_id(folder_url or sessions[session_id].get('folderUrl', ''))
        decisions = sessions[session_id].get('decisions', {})

        # Return status & summary for the 3 folders
        selected_ids = [pid for pid, d in decisions.items() if d == 'select']
        rejected_ids = [pid for pid, d in decisions.items() if d == 'reject']
        decide_ids = [pid for pid, d in decisions.items() if d == 'maybe']

        self.send_json_response(200, {
            "success": True,
            "folderId": folder_id,
            "folders": {
                "Selected": len(selected_ids),
                "Rejected": len(rejected_ids),
                "Decide": len(decide_ids)
            },
            "bridgeConfigured": bool(bridge_url or sessions[session_id].get('driveBridgeUrl'))
        })

    def handle_create_session(self, payload):
        title = payload.get('title', 'Event Photo Selection')
        photos = payload.get('photos', [])
        folder_url = payload.get('folderUrl', '')
        logo_url = payload.get('logoUrl', '')
        photographer_name = payload.get('photographerName', '')
        drive_bridge_url = payload.get('driveBridgeUrl', '')

        if not photos:
            self.send_json_response(400, {"success": False, "error": "Photos list cannot be empty."})
            return

        session_id = f"evt_{uuid.uuid4().hex[:8]}"
        sessions = load_sessions()
        
        sessions[session_id] = {
            "id": session_id,
            "title": title,
            "createdAt": int(time.time()),
            "folderUrl": folder_url,
            "driveBridgeUrl": drive_bridge_url,
            "photographerName": photographer_name,
            "logoUrl": logo_url,
            "photos": photos,
            "decisions": {},
            "lastActiveIndex": 0
        }
        save_sessions(sessions)

        network_url = self.get_network_url(session_id)
        local_url = f"http://localhost:{PORT}/?session={session_id}"

        self.send_json_response(200, {
            "success": True,
            "sessionId": session_id,
            "shareUrl": network_url,
            "networkUrl": network_url,
            "localUrl": local_url,
            "title": title,
            "totalPhotos": len(photos)
        })

    def handle_get_session(self, query_string):
        params = urllib.parse.parse_qs(query_string)
        session_id = params.get('id', [''])[0]

        if not session_id:
            self.send_json_response(400, {"success": False, "error": "Session ID required."})
            return

        sessions = load_sessions()
        if session_id not in sessions:
            self.send_json_response(404, {"success": False, "error": "Session not found."})
            return

        session = sessions[session_id]
        
        decisions = session.get('decisions', {})
        selected_count = sum(1 for v in decisions.values() if v == 'select')
        rejected_count = sum(1 for v in decisions.values() if v == 'reject')
        maybe_count = sum(1 for v in decisions.values() if v == 'maybe')
        total = len(session.get('photos', []))
        undecided_count = total - (selected_count + rejected_count + maybe_count)

        network_url = self.get_network_url(session_id)
        local_url = f"http://localhost:{PORT}/?session={session_id}"

        self.send_json_response(200, {
            "success": True,
            "session": session,
            "shareUrl": network_url,
            "networkUrl": network_url,
            "localUrl": local_url,
            "viewers": get_subscriber_count(session_id),
            "stats": {
                "selected": selected_count,
                "rejected": rejected_count,
                "maybe": maybe_count,
                "undecided": max(0, undecided_count),
                "total": total
            }
        })

    def handle_session_settings(self, payload):
        session_id = payload.get('sessionId')
        logo_url = payload.get('logoUrl')
        photographer_name = payload.get('photographerName')
        drive_bridge_url = payload.get('driveBridgeUrl')

        if not session_id:
            self.send_json_response(400, {"success": False, "error": "Session ID required."})
            return

        sessions = load_sessions()
        if session_id not in sessions:
            self.send_json_response(404, {"success": False, "error": "Session not found."})
            return

        if logo_url is not None:
            sessions[session_id]['logoUrl'] = logo_url
        if photographer_name is not None:
            sessions[session_id]['photographerName'] = photographer_name
        if drive_bridge_url is not None:
            sessions[session_id]['driveBridgeUrl'] = drive_bridge_url

        save_sessions(sessions)
        self.send_json_response(200, {"success": True, "session": sessions[session_id]})

    def handle_api_folder(self, query_string):
        params = urllib.parse.parse_qs(query_string)
        raw_url = params.get('url', [''])[0]
        raw_id = params.get('id', [''])[0]

        target = raw_url if raw_url else raw_id
        target_id = clean_folder_id(target)

        if not target_id:
            self.send_json_response(400, {
                "success": False,
                "error": "Google Drive Folder URL or ID is required."
            })
            return

        print(f"[API] Extracting photos from folder ID: {target_id}")
        sys.stdout.flush()

        # 1. Check if we already have this folder cached in sessions.json
        sessions = load_sessions()
        for sid, sdata in sessions.items():
            s_folder = sdata.get('folderUrl', '')
            if target_id in s_folder and sdata.get('photos'):
                print(f"[API] Found {len(sdata['photos'])} cached photos for folder {target_id} in session {sid}")
                self.send_json_response(200, {
                    "success": True,
                    "count": len(sdata['photos']),
                    "folderId": target_id,
                    "photos": sdata['photos']
                })
                return

        # 2. Fetch files using Google Drive API v3 (reliable, official)
        photos = []
        error_msg = ""
        IMAGE_MIMES = {
            'image/jpeg', 'image/jpg', 'image/png', 'image/webp',
            'image/heic', 'image/heif', 'image/gif', 'image/bmp',
            'image/tiff', 'image/raw', 'image/x-raw',
        }

        try:
            page_token = None
            page = 0
            while True:
                page += 1
                # Build API URL with pagination
                params_q = urllib.parse.urlencode({
                    'q': f"'{target_id}' in parents and trashed=false",
                    'key': GOOGLE_API_KEY,
                    'fields': 'nextPageToken,files(id,name,mimeType)',
                    'pageSize': 1000,
                    **({'pageToken': page_token} if page_token else {})
                })
                api_url = f"https://www.googleapis.com/drive/v3/files?{params_q}"

                req = urllib.request.Request(api_url, headers={
                    'User-Agent': 'selecto/1.0'
                })
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode('utf-8'))

                files = data.get('files', [])
                print(f"[Drive API] Page {page}: {len(files)} files")
                sys.stdout.flush()

                for f in files:
                    fid = f.get('id', '')
                    fname = f.get('name', '')
                    mime = f.get('mimeType', '')

                    # Accept image MIME types OR image file extensions
                    if mime in IMAGE_MIMES or is_image_file(fname):
                        photos.append({
                            "id": fid,
                            "title": fname or f"Photo_{fid[:8]}.jpg",
                            "url": f"https://drive.google.com/thumbnail?id={fid}&sz=w1920",
                            "preview": f"https://drive.google.com/thumbnail?id={fid}&sz=w600",
                            "thumb": f"https://drive.google.com/thumbnail?id={fid}&sz=w300",
                            "fullUrl": f"https://drive.google.com/thumbnail?id={fid}&sz=w2560",
                            "downloadUrl": f"https://drive.google.com/uc?export=download&id={fid}",
                            "fallbackUrl": f"https://lh3.googleusercontent.com/d/{fid}=w1920",
                            "source": "drive"
                        })

                page_token = data.get('nextPageToken')
                if not page_token:
                    break  # All pages fetched

        except Exception as e:
            error_msg = str(e)
            print(f"[Drive API Error] {e}")
            sys.stdout.flush()

        if not photos:
            self.send_json_response(200, {
                "success": False,
                "error": f"फोल्डरमधून फोटो मिळाले नाहीत. कृपया खात्री करा: फोल्डर 'Anyone with the link can view' असे share केले आहे का? ({error_msg[:300]})"
            })
            return

        print(f"[Drive API] ✅ {len(photos)} photos found in folder {target_id}")
        sys.stdout.flush()

        self.send_json_response(200, {
            "success": True,
            "count": len(photos),
            "folderId": target_id,
            "photos": photos
        })


    def handle_proxy_image(self, query_string):
        params = urllib.parse.parse_qs(query_string)
        file_id = params.get('id', [''])[0]
        custom_url = params.get('url', [''])[0]

        if file_id:
            target_url = f"https://lh3.googleusercontent.com/d/{file_id}=w2560"
        elif custom_url:
            target_url = custom_url
        else:
            self.send_error(400, "Image ID or URL required")
            return

        try:
            req = urllib.request.Request(target_url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                self.send_response(200)
                self.send_header('Content-Type', resp.headers.get('Content-Type', 'image/jpeg'))
                self.send_header('Cache-Control', 'public, max-age=86400')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(resp.read())
        except Exception:
            if file_id:
                try:
                    fallback = f"https://drive.google.com/thumbnail?id={file_id}&sz=w2560"
                    req2 = urllib.request.Request(fallback, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req2, timeout=10) as resp2:
                        self.send_response(200)
                        self.send_header('Content-Type', resp2.headers.get('Content-Type', 'image/jpeg'))
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(resp2.read())
                        return
                except Exception:
                    pass
            self.send_error(502, "Failed to proxy image")

    def get_admin_token_from_request(self):
        # 1. Check Cookie
        cookie_header = self.headers.get('Cookie', '')
        for cookie in cookie_header.split(';'):
            cookie = cookie.strip()
            if cookie.startswith('admin_token='):
                return cookie.split('=', 1)[1]
        # 2. Check Authorization header
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            return auth.split(' ', 1)[1]
        return None

    def is_authenticated_admin(self):
        token = self.get_admin_token_from_request()
        return verify_admin_token(token)

    # ── SAAS PHOTOGRAPHER AUTH & MONETIZATION ──
    def handle_google_login(self, payload):
        email = payload.get('email', '').strip().lower()
        name = payload.get('name', '').strip() or email.split('@')[0]
        picture = payload.get('picture', '')
        google_id = payload.get('googleId', '')

        if not email:
            self.send_json_response(400, {"success": False, "error": "Email is required"})
            return

        users = load_users()
        user = users.get(email)

        # Single Device Token Lock: Generate new device token on login
        new_token = uuid.uuid4().hex + uuid.uuid4().hex

        if not user:
            user = {
                "email": email,
                "name": name,
                "picture": picture,
                "googleId": google_id,
                "status": "pending_payment", # "pending_payment" | "active" | "expired" | "blocked"
                "plan": "none",              # "none" | "monthly" (₹499) | "yearly" (₹2999)
                "expires_at": "",
                "active_token": new_token,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "last_login": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            users[email] = user
        else:
            user['name'] = name or user.get('name', '')
            user['picture'] = picture or user.get('picture', '')
            user['active_token'] = new_token
            user['last_login'] = time.strftime("%Y-%m-%d %H:%M:%S")
            users[email] = user

        save_users(users)

        active = is_user_active(user)
        self.send_json_response(200, {
            "success": True,
            "token": new_token,
            "user": {
                "email": user['email'],
                "name": user['name'],
                "picture": user['picture'],
                "status": user['status'],
                "plan": user['plan'],
                "expires_at": user['expires_at'],
                "is_active": active
            }
        })

    def handle_user_profile(self, payload):
        email = payload.get('email', '').strip().lower()
        token = payload.get('token', '').strip()

        users = load_users()
        user = users.get(email)

        if not user:
            self.send_json_response(404, {"success": False, "error": "User not found"})
            return

        # Single Device Lock Check: Check if active token matches
        if token and user.get('active_token') and token != user.get('active_token'):
            self.send_json_response(401, {
                "success": False, 
                "error": "Single Device Lock: You have been logged in on another device.",
                "device_conflict": True
            })
            return

        active = is_user_active(user)
        self.send_json_response(200, {
            "success": True,
            "user": {
                "email": user['email'],
                "name": user['name'],
                "picture": user['picture'],
                "status": user['status'],
                "plan": user['plan'],
                "expires_at": user['expires_at'],
                "is_active": active
            }
        })

    def handle_payment_activate(self, payload):
        email = payload.get('email', '').strip().lower()
        plan = payload.get('plan', 'monthly') # "monthly" (₹499) or "yearly" (₹2999)
        payment_id = payload.get('paymentId', 'PAY_' + uuid.uuid4().hex[:10])

        users = load_users()
        user = users.get(email)

        if not user:
            self.send_json_response(404, {"success": False, "error": "User account not found"})
            return

        # Calculate expiration date
        now = time.time()
        days = 365 if plan == 'yearly' else 30
        exp_time = now + (days * 86400)
        expires_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(exp_time))

        user['status'] = 'active'
        user['plan'] = plan
        user['expires_at'] = expires_at
        user['last_payment_id'] = payment_id
        user['last_payment_date'] = time.strftime("%Y-%m-%d %H:%M:%S")
        users[email] = user
        save_users(users)

        print(f"[Payment Activated] User {email} activated for {plan} plan until {expires_at}")
        sys.stdout.flush()

        self.send_json_response(200, {
            "success": True,
            "message": f"Account activated successfully! Plan: {plan.upper()} (Valid until {expires_at})",
            "user": {
                "email": user['email'],
                "name": user['name'],
                "status": "active",
                "plan": plan,
                "expires_at": expires_at,
                "is_active": True
            }
        })

    def handle_admin_user_action(self, payload):
        if not self.is_authenticated_admin():
            self.send_json_response(401, {"success": False, "error": "Unauthorized"})
            return

        email = payload.get('email', '').strip().lower()
        action = payload.get('action', '') # "activate_monthly" | "activate_yearly" | "block" | "unblock"

        users = load_users()
        user = users.get(email)

        if not user:
            self.send_json_response(404, {"success": False, "error": "User not found"})
            return

        now = time.time()
        if action == 'activate_monthly':
            user['status'] = 'active'
            user['plan'] = 'monthly'
            user['expires_at'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now + (30 * 86400)))
        elif action == 'activate_yearly':
            user['status'] = 'active'
            user['plan'] = 'yearly'
            user['expires_at'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now + (365 * 86400)))
        elif action == 'block':
            user['status'] = 'blocked'
        elif action == 'unblock':
            user['status'] = 'pending_payment'

        users[email] = user
        save_users(users)

        self.send_json_response(200, {"success": True, "user": user})

    def handle_admin_login(self, payload):
        username = payload.get('username', '').strip()
        password = payload.get('password', '').strip()

        if username == ADMIN_USER and password == ADMIN_PASS:
            token = create_admin_token()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Set-Cookie', f'admin_token={token}; Path=/; HttpOnly; SameSite=Lax')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "token": token}).encode('utf-8'))
        else:
            self.send_json_response(401, {"success": False, "error": "Invalid Username or Password"})

    def handle_admin_logout(self):
        token = self.get_admin_token_from_request()
        if token in ADMIN_TOKENS:
            ADMIN_TOKENS.remove(token)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Set-Cookie', 'admin_token=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"success": True}).encode('utf-8'))

    def handle_admin_stats(self):
        if not self.is_authenticated_admin():
            self.send_json_response(401, {"success": False, "error": "Unauthorized. Please login to access Admin API."})
            return
        analytics = load_analytics()
        sessions = load_sessions()
        
        total_photos = 0
        total_selected = 0
        total_rejected = 0
        total_maybe = 0
        session_list = []

        for sid, s in sessions.items():
            photos = s.get('photos', [])
            decisions = s.get('decisions', {})
            
            sel_count = sum(1 for v in decisions.values() if v == 'select')
            rej_count = sum(1 for v in decisions.values() if v == 'reject')
            may_count = sum(1 for v in decisions.values() if v == 'maybe')

            total_photos += len(photos)
            total_selected += sel_count
            total_rejected += rej_count
            total_maybe += may_count

            live_viewers = get_subscriber_count(sid)

            session_list.append({
                "id": sid,
                "title": s.get('title', 'Untitled Event'),
                "created_at": s.get('created_at', ''),
                "photos_count": len(photos),
                "selected": sel_count,
                "rejected": rej_count,
                "maybe": may_count,
                "live_viewers": live_viewers,
                "folder_url": s.get('folderUrl', '')
            })

        session_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        users = load_users()
        user_list = []
        active_users_count = 0

        for u_email, u in users.items():
            act = is_user_active(u)
            if act: active_users_count += 1
            user_list.append({
                "email": u.get('email'),
                "name": u.get('name'),
                "status": u.get('status'),
                "plan": u.get('plan'),
                "expires_at": u.get('expires_at'),
                "created_at": u.get('created_at'),
                "last_login": u.get('last_login'),
                "is_active": act
            })

        self.send_json_response(200, {
            "success": True,
            "total_views": analytics.get("total_views", 0),
            "unique_visitors": len(analytics.get("unique_ips", [])),
            "last_visit": analytics.get("last_visit", ""),
            "total_sessions": len(sessions),
            "total_photos": total_photos,
            "total_selected": total_selected,
            "total_rejected": total_rejected,
            "total_maybe": total_maybe,
            "total_photographers": len(users),
            "active_subscriptions": active_users_count,
            "photographers": user_list,
            "sessions": session_list
        })

    def render_admin_login_page(self):
        html = '''<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>selecto — Admin Security Login</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/lucide@latest"></script>
  <link rel="stylesheet" href="/styles.css">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #080a0f; color: #f0f2f5; }
  </style>
</head>
<body class="min-h-screen flex items-center justify-center p-4">
  <div class="w-full max-w-md bg-[#0f1117] border border-white/10 rounded-3xl p-8 shadow-2xl space-y-6">
    
    <div class="flex items-center gap-3">
      <div class="w-12 h-12 rounded-2xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
        <i data-lucide="shield-check" class="w-6 h-6"></i>
      </div>
      <div>
        <h1 class="text-xl font-bold text-white tracking-tight">selecto Admin Login</h1>
        <p class="text-xs text-gray-400">Authorized Personnel & Studio Admin Access</p>
      </div>
    </div>

    <div id="loginError" class="hidden p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-semibold flex items-center gap-2">
      <i data-lucide="alert-circle" class="w-4 h-4 flex-shrink-0"></i>
      <span id="loginErrorText">Invalid credentials</span>
    </div>

    <form id="adminLoginForm" onsubmit="handleLogin(event)" class="space-y-4">
      <div>
        <label class="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">Admin Username</label>
        <div class="relative">
          <input id="loginUsername" type="text" required placeholder="Username" value="admin"
                 class="w-full bg-black/50 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition">
          <i data-lucide="user" class="w-4 h-4 text-gray-500 absolute left-3.5 top-1/2 -translate-y-1/2"></i>
        </div>
      </div>

      <div>
        <label class="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">Admin Password</label>
        <div class="relative">
          <input id="loginPassword" type="password" required placeholder="Password"
                 class="w-full bg-black/50 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition">
          <i data-lucide="lock" class="w-4 h-4 text-gray-500 absolute left-3.5 top-1/2 -translate-y-1/2"></i>
        </div>
      </div>

      <button id="loginBtn" type="submit" class="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs sm:text-sm transition flex items-center justify-center gap-2 cursor-pointer shadow-lg shadow-blue-600/30">
        <i data-lucide="key-round" class="w-4 h-4"></i>
        <span>Unlock Admin Portal</span>
      </button>
    </form>

    <div class="pt-4 border-t border-white/10 text-center text-[11px] text-gray-500">
      Protected by selecto Admin Security · AIKALAKAR Studio
    </div>
  </div>

  <script>
    if (window.lucide) window.lucide.createIcons();

    async function handleLogin(e) {
      e.preventDefault();
      const u = document.getElementById('loginUsername').value.trim();
      const p = document.getElementById('loginPassword').value.trim();
      const errorDiv = document.getElementById('loginError');
      const errorText = document.getElementById('loginErrorText');
      const btn = document.getElementById('loginBtn');

      if (!u || !p) return;

      btn.disabled = true;
      btn.innerHTML = `<div class="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin"></div><span>Authenticating...</span>`;
      errorDiv.classList.add('hidden');

      try {
        const res = await fetch('/api/admin/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: u, password: p })
        });
        const data = await res.json();
        if (data.success) {
          window.location.reload();
        } else {
          errorText.textContent = data.error || "Invalid Username or Password";
          errorDiv.classList.remove('hidden');
          btn.disabled = false;
          btn.innerHTML = `<i data-lucide="key-round" class="w-4 h-4"></i><span>Unlock Admin Portal</span>`;
          if (window.lucide) window.lucide.createIcons();
        }
      } catch(err) {
        errorText.textContent = "Connection error. Please try again.";
        errorDiv.classList.remove('hidden');
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="key-round" class="w-4 h-4"></i><span>Unlock Admin Portal</span>`;
        if (window.lucide) window.lucide.createIcons();
      }
    }
  </script>
</body>
</html>'''
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def handle_admin_dashboard(self, query_string=""):
        if not self.is_authenticated_admin():
            self.render_admin_login_page()
            return
        html = '''<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>selecto — Admin & Studio Analytics</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/lucide@latest"></script>
  <link rel="stylesheet" href="/styles.css">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #080a0f; color: #f0f2f5; }
  </style>
</head>
<body class="min-h-screen p-4 sm:p-8">
  <div class="max-w-7xl mx-auto space-y-8">
    
    <!-- Admin Header -->
    <header class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-white/10 pb-6">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
          <i data-lucide="layout-dashboard" class="w-5 h-5"></i>
        </div>
        <div>
          <h1 class="text-xl font-black text-white tracking-tight flex items-center gap-2">
            <span>selecto Admin Dashboard</span>
            <span class="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">LIVE</span>
          </h1>
          <p class="text-xs text-gray-400">Real-Time Studio Analytics, Page Visitors & Photo Selection Stats</p>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <a href="/" class="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-xs font-bold text-white transition flex items-center gap-2">
          <i data-lucide="arrow-left" class="w-4 h-4"></i>
          <span>Back to App</span>
        </a>
        <button onclick="fetchStats()" class="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-bold text-white transition flex items-center gap-2">
          <i data-lucide="refresh-cw" class="w-4 h-4"></i>
          <span>Refresh</span>
        </button>
        <button onclick="logoutAdmin()" class="px-4 py-2 rounded-xl bg-rose-500/20 hover:bg-rose-500 text-xs font-bold text-rose-300 hover:text-white border border-rose-500/30 transition flex items-center gap-2">
          <i data-lucide="log-out" class="w-4 h-4"></i>
          <span>Logout</span>
        </button>
      </div>
    </header>

    <!-- Overview Cards Grid -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="bg-[#0f1117] border border-white/10 rounded-2xl p-5">
        <div class="flex items-center justify-between text-gray-400 text-xs font-medium mb-2">
          <span>Total Page Visits</span>
          <i data-lucide="eye" class="w-4 h-4 text-blue-400"></i>
        </div>
        <div id="statTotalViews" class="text-2xl sm:text-3xl font-black text-white">0</div>
        <div id="statUniqueVisitors" class="text-[11px] text-gray-400 mt-1">0 Unique Visitors</div>
      </div>

      <div class="bg-[#0f1117] border border-white/10 rounded-2xl p-5">
        <div class="flex items-center justify-between text-gray-400 text-xs font-medium mb-2">
          <span>Active Sessions</span>
          <i data-lucide="folder-kanban" class="w-4 h-4 text-purple-400"></i>
        </div>
        <div id="statTotalSessions" class="text-2xl sm:text-3xl font-black text-white">0</div>
        <div id="statTotalPhotos" class="text-[11px] text-gray-400 mt-1">0 Total Photos</div>
      </div>

      <div class="bg-[#0f1117] border border-white/10 rounded-2xl p-5">
        <div class="flex items-center justify-between text-gray-400 text-xs font-medium mb-2">
          <span>Selected Photos</span>
          <i data-lucide="check-circle-2" class="w-4 h-4 text-emerald-400"></i>
        </div>
        <div id="statTotalSelected" class="text-2xl sm:text-3xl font-black text-emerald-400">0</div>
        <div class="text-[11px] text-gray-400 mt-1">Approved by Clients</div>
      </div>

      <div class="bg-[#0f1117] border border-white/10 rounded-2xl p-5">
        <div class="flex items-center justify-between text-gray-400 text-xs font-medium mb-2">
          <span>Rejected / Pending</span>
          <i data-lucide="help-circle" class="w-4 h-4 text-amber-400"></i>
        </div>
        <div class="flex items-baseline gap-2">
          <span id="statTotalRejected" class="text-xl font-bold text-rose-400">0</span>
          <span class="text-xs text-gray-400">/</span>
          <span id="statTotalMaybe" class="text-xl font-bold text-amber-400">0</span>
        </div>
        <div class="text-[11px] text-gray-400 mt-1">Rejected / Decide Later</div>
      </div>
    </div>

        <!-- Photographers & Subscriptions Management Table -->
    <div class="bg-[#0f1117] border border-white/10 rounded-2xl p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-base font-bold text-white flex items-center gap-2">
            <i data-lucide="users" class="w-4 h-4 text-amber-400"></i>
            <span>Registered Photographers &amp; Subscriptions</span>
          </h2>
          <p class="text-xs text-gray-400">Manage photographer accounts, activation plans &amp; license locks</p>
        </div>
        <div class="text-xs font-bold text-amber-400 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20">
          <span id="statActiveSubscribers">0</span> Active Paid Members
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead>
            <tr class="border-b border-white/10 text-gray-400 uppercase text-[10px] tracking-wider">
              <th class="py-3 px-4">Photographer</th>
              <th class="py-3 px-4">Email</th>
              <th class="py-3 px-4">Status</th>
              <th class="py-3 px-4">Plan</th>
              <th class="py-3 px-4">Expires At</th>
              <th class="py-3 px-4">Last Login</th>
              <th class="py-3 px-4">Admin Action</th>
            </tr>
          </thead>
          <tbody id="photographersTableBody" class="divide-y divide-white/5">
            <tr>
              <td colspan="7" class="py-6 text-center text-gray-400">Loading photographers data...</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Active Sessions Table -->
    <div class="bg-[#0f1117] border border-white/10 rounded-2xl p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-base font-bold text-white flex items-center gap-2">
            <i data-lucide="layers" class="w-4 h-4 text-blue-400"></i>
            <span>Photo Proofing Sessions</span>
          </h2>
          <p class="text-xs text-gray-400">Live active sessions and real-time decision status</p>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead>
            <tr class="border-b border-white/10 text-gray-400 uppercase text-[10px] tracking-wider">
              <th class="py-3 px-4">Event Title</th>
              <th class="py-3 px-4">Session ID</th>
              <th class="py-3 px-4">Photos</th>
              <th class="py-3 px-4">Selected</th>
              <th class="py-3 px-4">Rejected</th>
              <th class="py-3 px-4">Decide</th>
              <th class="py-3 px-4">Live Viewers</th>
              <th class="py-3 px-4">Actions</th>
            </tr>
          </thead>
          <tbody id="sessionsTableBody" class="divide-y divide-white/5">
            <tr>
              <td colspan="8" class="py-6 text-center text-gray-400">Loading live sessions data...</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>

  <script>
    async function fetchStats() {
      try {
        const res = await fetch('/api/admin/stats');
        const data = await res.json();
        if (!data.success) return;

        document.getElementById('statTotalViews').textContent = data.total_views;
        document.getElementById('statUniqueVisitors').textContent = `${data.unique_visitors} Unique Visitors`;
        document.getElementById('statTotalSessions').textContent = data.total_sessions;
        document.getElementById('statTotalPhotos').textContent = `${data.total_photos} Total Photos`;
        document.getElementById('statTotalSelected').textContent = data.total_selected;
        document.getElementById('statTotalRejected').textContent = data.total_rejected;
        document.getElementById('statTotalMaybe').textContent = data.total_maybe;

        const tbody = document.getElementById('sessionsTableBody');
        if (!data.sessions || data.sessions.length === 0) {
          tbody.innerHTML = `<tr><td colspan="8" class="py-6 text-center text-gray-400">No active proofing sessions yet. Create one from the main app!</td></tr>`;
          return;
        }

        tbody.innerHTML = data.sessions.map(s => `
          <tr class="hover:bg-white/5 transition">
            <td class="py-3.5 px-4 font-bold text-white">${escapeHtml(s.title)}</td>
            <td class="py-3.5 px-4 font-mono text-gray-400">${s.id}</td>
            <td class="py-3.5 px-4 font-mono text-white">${s.photos_count}</td>
            <td class="py-3.5 px-4 font-mono font-bold text-emerald-400">${s.selected}</td>
            <td class="py-3.5 px-4 font-mono font-bold text-rose-400">${s.rejected}</td>
            <td class="py-3.5 px-4 font-mono font-bold text-amber-400">${s.maybe}</td>
            <td class="py-3.5 px-4">
              <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full ${s.live_viewers > 0 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-bold' : 'bg-white/5 text-gray-400'}">
                <span class="w-1.5 h-1.5 rounded-full ${s.live_viewers > 0 ? 'bg-emerald-400 animate-pulse' : 'bg-gray-500'}"></span>
                ${s.live_viewers} Active
              </span>
            </td>
            <td class="py-3.5 px-4">
              <a href="/?session=${s.id}" target="_blank" class="px-3 py-1 rounded-lg bg-blue-600/20 hover:bg-blue-600 text-blue-300 hover:text-white border border-blue-500/30 transition text-[11px] font-semibold inline-flex items-center gap-1">
                <span>Open Portal</span>
                <i data-lucide="external-link" class="w-3 h-3"></i>
              </a>
            </td>
          </tr>
        `).join('');

        if (window.lucide) window.lucide.createIcons();
      } catch(err) {
        console.error("Fetch stats error:", err);
      }
    }

        async function logoutAdmin() {
      try {
        await fetch('/api/admin/logout', { method: 'POST' });
        window.location.reload();
      } catch(e) {
        window.location.reload();
      }
    }

    
    async function adminUserAction(email, action) {
      if (!confirm(`Perform action '${action}' for ${email}?`)) return;
      try {
        const res = await fetch('/api/admin/user-action', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, action })
        });
        const data = await res.json();
        if (data.success) {
          fetchStats();
        } else {
          alert("Error: " + (data.error || "Action failed"));
        }
      } catch(e) {
        alert("Action error: " + e.message);
      }
    }

    function escapeHtml(str) {
      return (str || '').replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    fetchStats();
    setInterval(fetchStats, 5000);
  </script>
</body>
</html>'''
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def send_json_response(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

def run():
    os.chdir(DIRECTORY)
    with ThreadedHTTPServer(("0.0.0.0", PORT), PhotoProofingHandler) as httpd:
        print("=" * 75)
        print("  📸 selecto - Photo Selection, Simplified.")
        print("  ⚡ Sub-30ms Server-Sent Events (SSE) Realtime Co-Viewing Stream Active")
        print(f"  💻 Local Mac:           http://localhost:{PORT}")
        print(f"  📱 Mobile / Client URL: http://{LOCAL_IP}:{PORT}")
        print("  ✅ Big 3 Buttons:       SELECT / REJECT / DECIDE")
        print("  📁 Google Drive Folders: Selected / Rejected / Decide Sync Ready")
        print("=" * 75)
        sys.stdout.flush()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")

if __name__ == "__main__":
    run()
