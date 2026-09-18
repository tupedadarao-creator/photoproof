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

PORT = int(os.environ.get("PORT", 8080))
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
# On Render, use /data for persistent storage; locally use app directory
_DATA_DIR = "/data" if os.path.isdir("/data") else DIRECTORY
DATA_FILE = os.path.join(_DATA_DIR, "sessions.json")

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

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        
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
            summary = f"""PhotoProof Studio - Selection Summary
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
        self.send_header('Content-Disposition', f'attachment; filename="PhotoProof_{title}_Organized.zip"')
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
                    'User-Agent': 'PhotoProof/1.0'
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
                            "url": f"https://lh3.googleusercontent.com/d/{fid}=w1920",
                            "preview": f"https://lh3.googleusercontent.com/d/{fid}=w600",
                            "thumb": f"https://lh3.googleusercontent.com/d/{fid}=w300",
                            "fullUrl": f"https://lh3.googleusercontent.com/d/{fid}=w2560",
                            "downloadUrl": f"https://drive.google.com/uc?export=download&id={fid}",
                            "fallbackUrl": f"https://drive.google.com/thumbnail?id={fid}&sz=w1920",
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
        print("  📸 PhotoProof Studio - Luxury iOS 18 Edition")
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
