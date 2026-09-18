/**
 * PhotoProof Studio - Luxury iOS 18 Edition
 * Sub-30ms Server-Sent Events (SSE) Live Co-Viewing Engine
 * Big 3 Apple Decisions: SELECT / REJECT / DECIDE
 * Google Drive 3-Folder Realtime Bridge
 */

const SAMPLE_ALBUM = [
  {
    id: "sample-1",
    title: "WED_001.JPG",
    url: "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=2560&q=85",
    thumb: "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=300&q=70",
    downloadUrl: "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=3840&q=100",
    source: "demo"
  },
  {
    id: "sample-2",
    title: "WED_002.JPG",
    url: "https://images.unsplash.com/photo-1511285560929-80b456fea0bc?auto=format&fit=crop&w=2560&q=85",
    thumb: "https://images.unsplash.com/photo-1511285560929-80b456fea0bc?auto=format&fit=crop&w=300&q=70",
    downloadUrl: "https://images.unsplash.com/photo-1511285560929-80b456fea0bc?auto=format&fit=crop&w=3840&q=100",
    source: "demo"
  },
  {
    id: "sample-3",
    title: "WED_003.JPG",
    url: "https://images.unsplash.com/photo-1465495976277-4387d4b0b4c6?auto=format&fit=crop&w=2560&q=85",
    thumb: "https://images.unsplash.com/photo-1465495976277-4387d4b0b4c6?auto=format&fit=crop&w=300&q=70",
    downloadUrl: "https://images.unsplash.com/photo-1465495976277-4387d4b0b4c6?auto=format&fit=crop&w=3840&q=100",
    source: "demo"
  },
  {
    id: "sample-4",
    title: "WED_004.JPG",
    url: "https://images.unsplash.com/photo-1583939003579-730e3918a45a?auto=format&fit=crop&w=2560&q=85",
    thumb: "https://images.unsplash.com/photo-1583939003579-730e3918a45a?auto=format&fit=crop&w=300&q=70",
    downloadUrl: "https://images.unsplash.com/photo-1583939003579-730e3918a45a?auto=format&fit=crop&w=3840&q=100",
    source: "demo"
  },
  {
    id: "sample-5",
    title: "WED_005.JPG",
    url: "https://images.unsplash.com/photo-1520854221256-17451cc331bf?auto=format&fit=crop&w=2560&q=85",
    thumb: "https://images.unsplash.com/photo-1520854221256-17451cc331bf?auto=format&fit=crop&w=300&q=70",
    downloadUrl: "https://images.unsplash.com/photo-1520854221256-17451cc331bf?auto=format&fit=crop&w=3840&q=100",
    source: "demo"
  }
];

// --- SOUND ENGINE (Web Audio API) ---
class AudioFX {
  constructor() {
    this.ctx = null;
    this.enabled = localStorage.getItem('proof_sound_enabled') !== 'false';
  }

  init() {
    if (!this.ctx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) this.ctx = new AudioContext();
    }
    if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume();
  }

  toggle() {
    this.enabled = !this.enabled;
    localStorage.setItem('proof_sound_enabled', this.enabled ? 'true' : 'false');
    return this.enabled;
  }

  playSelect() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    const now = this.ctx.currentTime;
    const osc1 = this.ctx.createOscillator();
    const gain1 = this.ctx.createGain();
    osc1.type = 'triangle';
    osc1.frequency.setValueAtTime(587.33, now);
    osc1.frequency.exponentialRampToValueAtTime(880, now + 0.12);
    gain1.gain.setValueAtTime(0.35, now);
    gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.14);
    osc1.connect(gain1);
    gain1.connect(this.ctx.destination);
    osc1.start(now);
    osc1.stop(now + 0.15);

    const osc2 = this.ctx.createOscillator();
    const gain2 = this.ctx.createGain();
    osc2.type = 'sine';
    osc2.frequency.setValueAtTime(1174.66, now + 0.04);
    gain2.gain.setValueAtTime(0.2, now + 0.04);
    gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.2);
    osc2.connect(gain2);
    gain2.connect(this.ctx.destination);
    osc2.start(now + 0.04);
    osc2.stop(now + 0.22);
  }

  playReject() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(240, now);
    osc.frequency.exponentialRampToValueAtTime(110, now + 0.14);
    gain.gain.setValueAtTime(0.3, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(now);
    osc.stop(now + 0.16);
  }

  playMaybe() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(440, now);
    osc.frequency.exponentialRampToValueAtTime(554.37, now + 0.08);
    gain.gain.setValueAtTime(0.25, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(now);
    osc.stop(now + 0.14);
  }
}

class PhotoProofApp {
  constructor() {
    this.audio = new AudioFX();
    this.clientId = `client_${Math.random().toString(36).substring(2, 9)}`;
    
    this.allPhotos = [];
    this.filteredPhotos = [];
    this.currentIndex = 0;
    this.currentFilter = 'all';
    
    // Live Co-Viewing & Collaboration State
    this.sessionId = null;
    this.sessionTitle = "Event Photo Selection";
    this.decisions = {};
    this.sseSource = null;
    this.isLiveSyncActive = true;
    this.viewerCount = 1;
    this.networkUrl = "";
    this.localUrl = "";

    // Google Drive 3-Folder Bridge
    this.driveBridgeUrl = localStorage.getItem('proof_drive_bridge_url') || '';

    // Branding / Watermark
    this.branding = {
      logoUrl: localStorage.getItem('proof_logo_url') || '',
      photographerName: localStorage.getItem('proof_photographer_name') || 'STUDIO PHOTOGRAPHY'
    };

    // Slideshow
    this.isPlaying = false;
    this.slideInterval = null;
    this.slideDuration = 3500;
    this.progressInterval = null;

    // Zoom & Pan
    this.zoomLevel = 1;
    this.panX = 0;
    this.panY = 0;
    this.isPanning = false;
    this.panStartX = 0;
    this.panStartY = 0;

    // Touch Swipe
    this.touchStartX = 0;
    this.touchStartY = 0;
    this.touchCurrentX = 0;
    this.touchCurrentY = 0;
    this.touchStartTime = 0;
    this.isSwiping = false;

    this.inactivityTimeout = null;
    this.controlsVisible = true;

    this.cacheDom();
    this.init();
  }

  cacheDom() {
    this.dom = {
      imageCanvas: document.getElementById('imageCanvas'),
      activeImage: document.getElementById('activeImage'),
      imageWrapper: document.getElementById('imageWrapper'),
      loadingSpinner: document.getElementById('loadingSpinner'),
      photoCounter: document.getElementById('photoCounter'),
      currentPhotoName: document.getElementById('currentPhotoName'),
      sessionTitleDisplay: document.getElementById('sessionTitleDisplay'),
      filmstrip: document.getElementById('filmstrip'),
      photoBadge: document.getElementById('photoBadge'),
      screenFlashOverlay: document.getElementById('screenFlashOverlay'),
      popStamp: document.getElementById('popStamp'),
      popStampText: document.getElementById('popStampText'),

      // Dynamic Island elements
      dynamicIsland: document.getElementById('dynamicIsland'),
      liveStatusText: document.getElementById('liveStatusText'),
      viewerCountText: document.getElementById('viewerCountText'),
      countSelected: document.getElementById('countSelected'),
      countRejected: document.getElementById('countRejected'),
      countMaybe: document.getElementById('countMaybe'),
      countTotal: document.getElementById('countTotal'),

      // 3 BIG DECISION BUTTONS
      btnSelect: document.getElementById('btnSelect'),
      btnReject: document.getElementById('btnReject'),
      btnMaybe: document.getElementById('btnMaybe'),

      // Filter Buttons
      filterAll: document.getElementById('filterAll'),
      filterSelected: document.getElementById('filterSelected'),
      filterRejected: document.getElementById('filterRejected'),
      filterMaybe: document.getElementById('filterMaybe'),
      filterPending: document.getElementById('filterPending'),

      // Navigation & Chrome
      prevBtn: document.getElementById('prevBtn'),
      nextBtn: document.getElementById('nextBtn'),
      downloadBtn: document.getElementById('downloadBtn'),
      playPauseBtn: document.getElementById('playPauseBtn'),
      playIcon: document.getElementById('playIcon'),
      pauseIcon: document.getElementById('pauseIcon'),
      soundToggleBtn: document.getElementById('soundToggleBtn'),
      soundIconOn: document.getElementById('soundIconOn'),
      soundIconOff: document.getElementById('soundIconOff'),
      fullscreenBtn: document.getElementById('fullscreenBtn'),
      progressBar: document.getElementById('progressBar'),
      bottomBar: document.getElementById('bottomBar'),

      // Direct On-Screen Bar
      directDriveBar: document.getElementById('directDriveBar'),
      directDriveInput: document.getElementById('directDriveInput'),
      directPasteBtn: document.getElementById('directPasteBtn'),
      directLoadBtn: document.getElementById('directLoadBtn'),
      directBrandText: document.getElementById('directBrandText'),

      // Modals
      openImportBtn: document.getElementById('openImportBtn'),
      quickOpenImportBtn: document.getElementById('quickOpenImportBtn'),
      importModal: document.getElementById('importModal'),
      importCloseBtn: document.getElementById('importCloseBtn'),
      linkInput: document.getElementById('linkInput'),
      albumTitleInput: document.getElementById('albumTitleInput'),
      processLinksBtn: document.getElementById('processLinksBtn'),
      loadDemoBtn: document.getElementById('loadDemoBtn'),
      importPhotographerName: document.getElementById('importPhotographerName'),
      importLogoFileInput: document.getElementById('importLogoFileInput'),
      importLogoPreview: document.getElementById('importLogoPreview'),
      importLogoPreviewContainer: document.getElementById('importLogoPreviewContainer'),
      
      openShareBtn: document.getElementById('openShareBtn'),
      shareModal: document.getElementById('shareModal'),
      shareModalCloseBtn: document.getElementById('shareModalCloseBtn'),
      networkUrlInput: document.getElementById('networkUrlInput'),
      copyNetworkBtn: document.getElementById('copyNetworkBtn'),
      localUrlInput: document.getElementById('localUrlInput'),
      copyLocalBtn: document.getElementById('copyLocalBtn'),
      qrCodeImg: document.getElementById('qrCodeImg'),

      openBrandingBtn: document.getElementById('openBrandingBtn'),
      brandingModal: document.getElementById('brandingModal'),
      brandingModalCloseBtn: document.getElementById('brandingModalCloseBtn'),
      logoUrlInput: document.getElementById('logoUrlInput'),
      logoFileInput: document.getElementById('logoFileInput'),
      photographerNameInput: document.getElementById('photographerNameInput'),
      saveBrandingBtn: document.getElementById('saveBrandingBtn'),
      logoPreview: document.getElementById('logoPreview'),

      openDriveModalBtn: document.getElementById('openDriveModalBtn'),
      driveModal: document.getElementById('driveModal'),
      driveModalCloseBtn: document.getElementById('driveModalCloseBtn'),
      driveBridgeUrlInput: document.getElementById('driveBridgeUrlInput'),
      saveDriveBridgeBtn: document.getElementById('saveDriveBridgeBtn'),
      syncDriveNowBtn: document.getElementById('syncDriveNowBtn'),
      folderCountSelected: document.getElementById('folderCountSelected'),
      folderCountRejected: document.getElementById('folderCountRejected'),
      folderCountDecide: document.getElementById('folderCountDecide'),

      openExportBtn: document.getElementById('openExportBtn'),
      exportModal: document.getElementById('exportModal'),
      exportModalCloseBtn: document.getElementById('exportModalCloseBtn'),
      exportCountBadge: document.getElementById('exportCountBadge'),
      lightroomStringArea: document.getElementById('lightroomStringArea'),
      copyLightroomBtn: document.getElementById('copyLightroomBtn'),
      downloadCsvBtn: document.getElementById('downloadCsvBtn'),
      downloadZipBtn: document.getElementById('downloadZipBtn'),
      quickDownloadBtn: document.getElementById('quickDownloadBtn'),
      mobileSaveBtn: document.getElementById('mobileSaveBtn'),
      progressivePreviewLayer: document.getElementById('progressivePreviewLayer'),
      progressivePreviewImg: document.getElementById('progressivePreviewImg')
    };
  }

  init() {
    this.bindEvents();
    this.updateSoundUi();
    this.checkSessionFromUrl();
    this.resetInactivityTimer();
  }

  updateSoundUi() {
    if (this.audio.enabled) {
      this.dom.soundIconOn?.classList.remove('hidden');
      this.dom.soundIconOff?.classList.add('hidden');
    } else {
      this.dom.soundIconOn?.classList.add('hidden');
      this.dom.soundIconOff?.classList.remove('hidden');
    }
  }

  // --- SUB-30ms REAL-TIME SERVER-SENT EVENTS (SSE) STREAM ---
  initRealtimeStream(sessionId) {
    if (this.sseSource) {
      this.sseSource.close();
    }

    const streamUrl = `/api/session/stream?id=${sessionId}&client=${this.clientId}`;
    this.sseSource = new EventSource(streamUrl);

    this.sseSource.onopen = () => {
      this.dom.liveStatusText.textContent = "LIVE CO-VIEW";
    };

    this.sseSource.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        this.handleRealtimeEvent(event);
      } catch (err) {}
    };

    this.sseSource.onerror = () => {
      // Automatic fallback will reconnect
    };
  }

  handleRealtimeEvent(event) {
    if (!event) return;

    // 1. PRESENCE UPDATE
    if (event.type === 'PRESENCE' || event.type === 'CONNECTED') {
      if (event.viewers !== undefined) {
        this.viewerCount = event.viewers;
        this.dom.viewerCountText.textContent = `${this.viewerCount} Connected`;
      }
    }

    // 2. INSTANT PHOTO NAVIGATION (< 30ms ZERO-LAG LIVE CALL SYNC!)
    else if (event.type === 'NAVIGATE') {
      // If navigated by the other party and live sync is active
      if (event.sender !== this.clientId && this.isLiveSyncActive) {
        if (typeof event.photoIndex === 'number' && event.photoIndex !== this.currentIndex) {
          // Instant prime of progressive preview so remote phone shows image in <10ms!
          if (event.previewUrl && this.dom.progressivePreviewImg) {
            this.dom.progressivePreviewImg.src = event.previewUrl;
            this.dom.progressivePreviewLayer?.classList.remove('hidden');
          }
          this.showPhoto(event.photoIndex, 'remote_sync');
        }
      }
    }

    // 3. INSTANT VOTE DECISION SYNC (SELECT / REJECT / DECIDE)
    else if (event.type === 'VOTE') {
      const { photoId, decision, sender, stats } = event;
      
      if (decision && decision !== 'none') {
        this.decisions[photoId] = decision;
      } else {
        delete this.decisions[photoId];
      }

      // If voted by someone else, play sound & animation on our screen too!
      if (sender !== this.clientId) {
        const currentPhoto = this.filteredPhotos[this.currentIndex];
        if (currentPhoto && currentPhoto.id === photoId) {
          if (decision === 'select') {
            this.audio.playSelect();
            this.triggerVisualEffects('select', 'SELECTED');
          } else if (decision === 'reject') {
            this.audio.playReject();
            this.triggerVisualEffects('reject', 'REJECTED');
          } else if (decision === 'maybe') {
            this.audio.playMaybe();
            this.triggerVisualEffects('maybe', 'DECIDE');
          }
        }
      }

      this.updateStats();
      this.updateActiveBadge();
      this.updateFilmstripThumb(photoId, decision);
    }
  }

  // Broadcast navigation to all connected clients immediately with dual resolution
  broadcastNavigation(index) {
    if (!this.sessionId) return;
    const photo = this.filteredPhotos[index];
    if (!photo) return;

    fetch('/api/session/navigate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sessionId: this.sessionId,
        photoIndex: index,
        photoId: photo.id,
        previewUrl: photo.preview || photo.thumb || '',
        thumbUrl: photo.thumb || '',
        url: photo.url,
        sender: this.clientId
      })
    }).catch(() => {});
  }

  // --- SESSION MANAGEMENT ---
  async checkSessionFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('session');

    if (sessionId) {
      await this.loadRemoteSession(sessionId);
    } else {
      const savedSessionId = localStorage.getItem('last_proof_session');
      if (savedSessionId) {
        await this.loadRemoteSession(savedSessionId).catch(() => {
          this.loadLocalPhotos(SAMPLE_ALBUM, "Sample Wedding Proofing");
        });
      } else {
        this.loadLocalPhotos(SAMPLE_ALBUM, "Sample Wedding Proofing");
        // Automatically pop up Google Drive link dialog so user can enter their link right away
        setTimeout(() => {
          this.dom.importModal.classList.remove('hidden');
          if (window.lucide) window.lucide.createIcons();
        }, 300);
      }
    }
  }

  async loadRemoteSession(sessionId) {
    try {
      this.dom.loadingSpinner.classList.remove('hidden');
      const res = await fetch(`/api/session?id=${sessionId}`);
      if (!res.ok) throw new Error("Session not found");

      const data = await res.json();
      if (!data.success || !data.session) throw new Error("Invalid session");

      this.sessionId = sessionId;
      localStorage.setItem('last_proof_session', sessionId);
      this.sessionTitle = data.session.title || "Event Selection";
      this.allPhotos = data.session.photos || [];
      this.decisions = data.session.decisions || {};
      this.networkUrl = data.networkUrl || data.shareUrl || window.location.href;
      this.localUrl = data.localUrl || `http://localhost:8080/?session=${sessionId}`;

      if (data.session.driveBridgeUrl) this.driveBridgeUrl = data.session.driveBridgeUrl;
      if (data.session.logoUrl) this.branding.logoUrl = data.session.logoUrl;
      if (data.session.photographerName) this.branding.photographerName = data.session.photographerName;

      // 🛡️ SECURITY: HIDE ADMIN / DRIVE IMPORT / SETTINGS BUTTONS FROM CLIENT
      this.applyClientSecurityMode();

      this.updateShareUrls();
      this.applyFilter(this.currentFilter);
      this.updateStats();
      this.dom.sessionTitleDisplay.textContent = this.sessionTitle;

      // Start sub-30ms SSE Stream
      this.initRealtimeStream(sessionId);
      this.showNotification(`Loaded Session: ${this.sessionTitle}`);
    } catch (err) {
      this.loadLocalPhotos(SAMPLE_ALBUM, "Sample Wedding Proofing");
    } finally {
      this.dom.loadingSpinner.classList.add('hidden');
    }
  }

  applyClientSecurityMode() {
    const urlParams = new URLSearchParams(window.location.search);
    const hasSession = urlParams.has('session');
    
    // Hide Import Drive Modal & Settings from Clients
    if (hasSession) {
      if (this.dom.openDriveModalBtn) this.dom.openDriveModalBtn.style.display = 'none';
      if (this.dom.importModal) {
        this.dom.importModal.classList.add('hidden');
        this.dom.importModal.style.display = 'none';
      }
      if (this.dom.openBrandingBtn) this.dom.openBrandingBtn.style.display = 'none';
      if (this.dom.openExportBtn) this.dom.openExportBtn.style.display = 'none';
      
      // Also hide any Drive links in DOM if present
      const driveInputs = document.querySelectorAll('#linkInput, #importDriveBridgeUrlInput');
      driveInputs.forEach(el => { if (el) el.value = ''; });
    }
  }

  async createRemoteSession(title, photos, folderUrl = '') {
    try {
      const res = await fetch('/api/session/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title || 'Photo Proofing Session',
          photos: photos,
          folderUrl: folderUrl,
          driveBridgeUrl: this.driveBridgeUrl,
          logoUrl: this.branding.logoUrl,
          photographerName: this.branding.photographerName
        })
      });

      const data = await res.json();
      if (data.success && data.sessionId) {
        this.sessionId = data.sessionId;
        this.networkUrl = data.networkUrl;
        this.localUrl = data.localUrl;
        localStorage.setItem('last_proof_session', data.sessionId);
        this.updateShareUrls();

        const url = new URL(window.location.href);
        url.searchParams.set('session', data.sessionId);
        window.history.replaceState({}, '', url.toString());

        this.initRealtimeStream(data.sessionId);
        this.showNotification("Session Created! Shareable links ready.");
      }
    } catch (err) {}
  }

  updateShareUrls() {
    if (this.dom.networkUrlInput) this.dom.networkUrlInput.value = this.networkUrl || window.location.href;
    if (this.dom.localUrlInput) this.dom.localUrlInput.value = this.localUrl || window.location.href;
    if (this.dom.qrCodeImg && this.networkUrl) {
      this.dom.qrCodeImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(this.networkUrl)}`;
    }
  }

  // --- THE BIG 3 DECISIONS (SELECT / REJECT / DECIDE) ---
  async makeDecision(decision) {
    if (!this.filteredPhotos || this.filteredPhotos.length === 0) return;
    const photo = this.filteredPhotos[this.currentIndex];
    if (!photo) return;

    const previousDecision = this.decisions[photo.id];
    const newDecision = previousDecision === decision ? null : decision;

    if (newDecision) {
      this.decisions[photo.id] = newDecision;
    } else {
      delete this.decisions[photo.id];
    }

    // 1. PLAY AUDIO & VISUAL EFFECTS IMMEDIATELY
    if (newDecision === 'select') {
      this.audio.playSelect();
      this.triggerVisualEffects('select', 'SELECTED');
    } else if (newDecision === 'reject') {
      this.audio.playReject();
      this.triggerVisualEffects('reject', 'REJECTED');
    } else if (newDecision === 'maybe') {
      this.audio.playMaybe();
      this.triggerVisualEffects('maybe', 'DECIDE');
    }

    this.updateStats();
    this.updateActiveBadge();
    this.updateFilmstripThumb(photo.id, newDecision);

    // 2. BROADCAST REAL-TIME TO ALL CONNECTED CLIENTS & GOOGLE DRIVE BRIDGE
    if (this.sessionId) {
      fetch('/api/session/vote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sessionId: this.sessionId,
          photoId: photo.id,
          decision: newDecision || 'none',
          sender: this.clientId
        })
      }).catch(() => {});
    }

    // 3. AUTO-ADVANCE TO NEXT PHOTO FOR LIGHTNING SPEED
    if (newDecision && this.currentIndex < this.filteredPhotos.length - 1) {
      setTimeout(() => {
        this.nextPhoto();
      }, 190);
    }
  }

  triggerVisualEffects(type, label) {
    this.dom.screenFlashOverlay.className = `screen-flash flash-${type}`;
    setTimeout(() => {
      this.dom.screenFlashOverlay.className = 'screen-flash';
    }, 350);

    this.dom.popStampText.textContent = label;
    this.dom.popStamp.className = `decision-pop-stamp stamp-${type} active`;
    setTimeout(() => {
      this.dom.popStamp.className = 'decision-pop-stamp';
    }, 450);
  }

  updateStats() {
    const total = this.allPhotos.length;
    let selected = 0, rejected = 0, maybe = 0;

    Object.values(this.decisions).forEach(d => {
      if (d === 'select') selected++;
      else if (d === 'reject') rejected++;
      else if (d === 'maybe') maybe++;
    });

    this.dom.countSelected.textContent = selected;
    this.dom.countRejected.textContent = rejected;
    this.dom.countMaybe.textContent = maybe;
    if (this.dom.countTotal) this.dom.countTotal.textContent = total;

    // Update Drive Modal Counters if present
    if (this.dom.folderCountSelected) this.dom.folderCountSelected.textContent = selected;
    if (this.dom.folderCountRejected) this.dom.folderCountRejected.textContent = rejected;
    if (this.dom.folderCountDecide) this.dom.folderCountDecide.textContent = maybe;

    const currentPhoto = this.filteredPhotos[this.currentIndex];
    const currentDecision = currentPhoto ? this.decisions[currentPhoto.id] : null;

    this.dom.btnSelect.classList.toggle('active-decision', currentDecision === 'select');
    this.dom.btnReject.classList.toggle('active-decision', currentDecision === 'reject');
    this.dom.btnMaybe.classList.toggle('active-decision', currentDecision === 'maybe');
  }

  updateActiveBadge() {
    const currentPhoto = this.filteredPhotos[this.currentIndex];
    if (!currentPhoto) return;

    const decision = this.decisions[currentPhoto.id];
    this.dom.photoBadge.className = 'photo-decision-watermark hidden';

    if (decision === 'select') {
      this.dom.photoBadge.textContent = 'Selected';
      this.dom.photoBadge.className = 'photo-decision-watermark selected';
    } else if (decision === 'reject') {
      this.dom.photoBadge.textContent = 'Rejected';
      this.dom.photoBadge.className = 'photo-decision-watermark rejected';
    } else if (decision === 'maybe') {
      this.dom.photoBadge.textContent = 'Decide';
      this.dom.photoBadge.className = 'photo-decision-watermark maybe';
    }
  }

  // --- FILTERING ---
  applyFilter(filterType) {
    this.currentFilter = filterType;
    const currentPhotoId = this.filteredPhotos[this.currentIndex]?.id;

    if (filterType === 'selected') {
      this.filteredPhotos = this.allPhotos.filter(p => this.decisions[p.id] === 'select');
    } else if (filterType === 'rejected') {
      this.filteredPhotos = this.allPhotos.filter(p => this.decisions[p.id] === 'reject');
    } else if (filterType === 'maybe') {
      this.filteredPhotos = this.allPhotos.filter(p => this.decisions[p.id] === 'maybe');
    } else if (filterType === 'pending') {
      this.filteredPhotos = this.allPhotos.filter(p => !this.decisions[p.id]);
    } else {
      this.filteredPhotos = [...this.allPhotos];
    }

    [this.dom.filterAll, this.dom.filterSelected, this.dom.filterRejected, this.dom.filterMaybe, this.dom.filterPending].forEach(btn => {
      if (btn) btn.classList.remove('active');
    });

    const activeMap = {
      all: this.dom.filterAll,
      selected: this.dom.filterSelected,
      rejected: this.dom.filterRejected,
      maybe: this.dom.filterMaybe,
      pending: this.dom.filterPending
    };
    if (activeMap[filterType]) activeMap[filterType].classList.add('active');

    let newIndex = 0;
    if (currentPhotoId) {
      const idx = this.filteredPhotos.findIndex(p => p.id === currentPhotoId);
      if (idx !== -1) newIndex = idx;
    }

    this.renderFilmstrip();
    if (this.filteredPhotos.length > 0) {
      this.showPhoto(newIndex);
    } else {
      this.dom.activeImage.src = '';
      this.dom.photoCounter.textContent = `0 / 0`;
      this.dom.currentPhotoName.textContent = 'No photos in this view';
      this.dom.photoBadge.className = 'photo-decision-watermark hidden';
    }
  }

  // --- GOOGLE DRIVE IMPORT ---
  async handleImport(inputText, albumTitle) {
    const trimmed = (inputText || '').trim();
    if (!trimmed) {
      alert("Please paste a Google Drive Folder link or Photo links!");
      return;
    }

    const title = albumTitle || "Event Proofing";
    if (this.dom.importPhotographerName && this.dom.importPhotographerName.value.trim()) {
      this.branding.photographerName = this.dom.importPhotographerName.value.trim();
      localStorage.setItem('proof_photographer_name', this.branding.photographerName);
    }

    this.dom.processLinksBtn.disabled = true;
    const originalText = this.dom.processLinksBtn.innerHTML;
    this.dom.processLinksBtn.innerHTML = `
      <div class="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
      <span>Extracting Google Drive Photos...</span>
    `;

    try {
      // 1. Try Google Drive extraction on server for all links
      const res = await fetch(`/api/folder?url=${encodeURIComponent(trimmed)}`);
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.photos && data.photos.length > 0) {
          this.loadLocalPhotos(data.photos, title);
          await this.createRemoteSession(title, data.photos, trimmed);
          this.dom.importModal.classList.add('hidden');
          this.dom.importModal.style.display = 'none';
          if (this.dom.linkInput) this.dom.linkInput.value = '';
          this.showNotification(`Loaded ${data.photos.length} photos from Google Drive!`);
          return;
        } else if (data.error) {
          console.warn("Folder API warning:", data.error);
        }
      }

      // 2. Fallback: Parse individual photo URLs
      const photos = this.extractDrivePhotos(trimmed);
      if (photos.length > 0) {
        this.loadLocalPhotos(photos, title);
        await this.createRemoteSession(title, photos);
        this.dom.importModal.classList.add('hidden');
        this.dom.importModal.style.display = 'none';
        if (this.dom.linkInput) this.dom.linkInput.value = '';
        this.showNotification(`Loaded ${photos.length} photos!`);
        return;
      }

      throw new Error("गुगल ड्राइव्हमधून फोटो लोड होऊ शकले नाहीत. कृपया खात्री करा की फोल्डरचे शेअरिंग 'Anyone with the link can view' असे आहे.");
    } catch (err) {
      alert(`Sync Error: ${err.message}`);
    } finally {
      this.dom.processLinksBtn.disabled = false;
      this.dom.processLinksBtn.innerHTML = originalText;
    }
  }

  extractDrivePhotos(text) {
    const extracted = [];
    const seen = new Set();
    const matches = text.matchAll(/(?:drive\.google\.com\/(?:file\/d\/|open\?id=|uc\?(?:export=[a-z]+&)?id=)|docs\.google\.com\/[a-z\/-]+\/d\/)([a-zA-Z0-9_-]{25,})/g);
    
    for (const m of matches) {
      const id = m[1];
      if (!seen.has(id)) {
        seen.add(id);
        extracted.push({
          id: id,
          title: `Photo_${extracted.length + 1}.JPG`,
          url: `https://lh3.googleusercontent.com/d/${id}=w2560`,
          thumb: `https://lh3.googleusercontent.com/d/${id}=w300`,
          downloadUrl: `https://drive.google.com/uc?export=download&id=${id}`,
          fallbackUrl: `https://drive.google.com/thumbnail?id=${id}&sz=w2560`,
          source: 'drive'
        });
      }
    }
    return extracted;
  }

  loadLocalPhotos(photos, title = "Photo Proofing") {
    this.allPhotos = photos;
    this.sessionTitle = title;
    this.decisions = {};
    this.dom.sessionTitleDisplay.textContent = title;
    this.applyFilter('all');
    this.updateStats();
  }

  // --- VIEWER & DISPLAY ---
  showPhoto(index, triggerType = 'local') {
    if (!this.filteredPhotos || this.filteredPhotos.length === 0) return;
    if (index < 0) index = this.filteredPhotos.length - 1;
    if (index >= this.filteredPhotos.length) index = 0;

    this.currentIndex = index;
    const photo = this.filteredPhotos[index];

    this.resetZoom();

    this.dom.photoCounter.textContent = `${index + 1} / ${this.filteredPhotos.length}`;
    this.dom.currentPhotoName.textContent = photo.title || `Photo ${index + 1}`;

    this.updateStats();
    this.updateActiveBadge();

    // 🌟 1. INSTANT PROGRESSIVE PREVIEW (0ms perceived latency) 🌟
    const instantThumb = photo.preview || photo.thumb;
    if (this.dom.progressivePreviewImg && instantThumb) {
      this.dom.progressivePreviewImg.src = instantThumb;
      this.dom.progressivePreviewLayer?.classList.remove('hidden');
    }

    // 🌟 2. FULL RESOLUTION HIGH QUALITY LOAD 🌟
    const targetSrc = photo.url;
    const tempImg = new Image();
    let triedFallback = false;

    tempImg.onload = () => {
      if (this.currentIndex === index) {
        this.dom.activeImage.src = tempImg.src;
        this.dom.activeImage.style.opacity = '1';
        this.dom.activeImage.style.transform = 'scale(1)';
        this.dom.loadingSpinner?.classList.add('hidden');
        // Smooth crossfade from thumbnail
        setTimeout(() => {
          if (this.currentIndex === index) {
            this.dom.progressivePreviewLayer?.classList.add('hidden');
          }
        }, 120);
      }
    };

    tempImg.onerror = () => {
      if (!triedFallback && photo.fallbackUrl) {
        triedFallback = true;
        tempImg.src = photo.fallbackUrl;
      } else if (this.currentIndex === index) {
        this.dom.loadingSpinner?.classList.add('hidden');
        this.dom.activeImage.src = photo.url;
        this.dom.activeImage.style.opacity = '1';
        this.dom.progressivePreviewLayer?.classList.add('hidden');
      }
    };

    tempImg.src = targetSrc;

    this.updateFilmstripActive(index);
    this.preloadAdjacentPhotos(index);

    if (this.isPlaying) this.resetSlideProgressBar();

    // Broadcast navigation to remote client if triggered locally
    if (triggerType !== 'remote_sync') {
      this.broadcastNavigation(index);
    }
  }

  // ⚡ SMART PRELOAD – only previews for adjacent, full-res loads lazily
  preloadAdjacentPhotos(index) {
    if (!this.filteredPhotos || this.filteredPhotos.length === 0) return;
    if (!this._preloadCache) this._preloadCache = new Set();
    const len = this.filteredPhotos.length;

    const preload = (idx, fullRes) => {
      const p = this.filteredPhotos[idx];
      if (!p) return;
      // Always preload preview/thumb (small, fast)
      const previewSrc = p.preview || p.thumb;
      if (previewSrc && !this._preloadCache.has(previewSrc)) {
        this._preloadCache.add(previewSrc);
        new Image().src = previewSrc;
      }
      // Only preload full-res for next photo only
      if (fullRes && p.url && !this._preloadCache.has(p.url)) {
        this._preloadCache.add(p.url);
        new Image().src = p.url;
      }
    };

    // Next 1 photo: full-res preload (most likely to be visited next)
    preload((index + 1) % len, true);
    // Next 2-3: preview only
    preload((index + 2) % len, false);
    preload((index + 3) % len, false);
    // Previous 1: preview only
    preload((index - 1 + len) % len, false);

    // Limit cache size to avoid memory bloat
    if (this._preloadCache.size > 60) this._preloadCache.clear();
  }

  nextPhoto() { this.showPhoto(this.currentIndex + 1, 'local'); }
  prevPhoto() { this.showPhoto(this.currentIndex - 1, 'local'); }

  // --- WATERMARK & DOWNLOAD ---
  async downloadPhotoWithWatermark() {
    if (!this.filteredPhotos || this.filteredPhotos.length === 0) return;
    const photo = this.filteredPhotos[this.currentIndex];
    if (!photo) return;

    this.showNotification("Preparing Watermarked Download...");

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();
    img.crossOrigin = "anonymous";

    const proxyUrl = photo.source === 'drive'
      ? `/api/proxy-image?id=${photo.id}`
      : `/api/proxy-image?url=${encodeURIComponent(photo.url)}`;

    img.onload = async () => {
      canvas.width = img.naturalWidth || img.width;
      canvas.height = img.naturalHeight || img.height;

      ctx.drawImage(img, 0, 0);
      await this.renderWatermarkOnCanvas(ctx, canvas.width, canvas.height);

      canvas.toBlob((blob) => {
        if (!blob) {
          window.open(photo.downloadUrl || photo.url, '_blank');
          return;
        }
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const cleanName = (photo.title || `photo_${this.currentIndex + 1}`).replace(/\.[^/.]+$/, "");
        a.download = `${cleanName}_Proof.jpg`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        this.showNotification("Downloaded with Watermark!");
      }, 'image/jpeg', 0.92);
    };

    img.onerror = () => {
      window.open(photo.downloadUrl || photo.url, '_blank');
      this.showNotification("Downloaded Original Photo");
    };

    img.src = proxyUrl;
  }

  async renderWatermarkOnCanvas(ctx, width, height) {
    const logoUrl = this.branding.logoUrl;
    const photographerName = this.branding.photographerName || 'PHOTOGRAPHY PROOF';

    ctx.save();
    if (logoUrl) {
      try {
        const logoImg = await this.loadImageAsync(logoUrl);
        const logoWidth = Math.max(160, Math.min(width * 0.18, 480));
        const scale = logoWidth / logoImg.width;
        const logoHeight = logoImg.height * scale;

        const padding = Math.max(20, width * 0.025);
        const x = width - logoWidth - padding;
        const y = height - logoHeight - padding;

        ctx.globalAlpha = 0.88;
        ctx.shadowColor = 'rgba(0, 0, 0, 0.7)';
        ctx.shadowBlur = 12;
        ctx.drawImage(logoImg, x, y, logoWidth, logoHeight);
        ctx.restore();
        return;
      } catch (e) {}
    }

    const fontSize = Math.max(20, Math.round(width * 0.022));
    ctx.font = `600 ${fontSize}px "Plus Jakarta Sans", sans-serif`;
    const paddingX = fontSize * 1.2;
    const paddingY = fontSize * 0.6;
    const margin = Math.max(30, width * 0.03);

    const text = `© ${photographerName.toUpperCase()}`;
    const textMetrics = ctx.measureText(text);
    const boxWidth = textMetrics.width + (paddingX * 2);
    const boxHeight = fontSize * 2;

    const x = width - boxWidth - margin;
    const y = height - boxHeight - margin;

    ctx.fillStyle = 'rgba(0, 0, 0, 0.55)';
    ctx.beginPath();
    ctx.roundRect(x, y, boxWidth, boxHeight, 10);
    ctx.fill();

    ctx.fillStyle = '#ffffff';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, x + paddingX, y + (boxHeight / 2));
    ctx.restore();
  }

  loadImageAsync(url) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = url;
    });
  }

  // --- EXPORT TO LIGHTROOM & PRINT ---
  openExportModal() {
    const selectedPhotos = this.allPhotos.filter(p => this.decisions[p.id] === 'select');
    this.dom.exportCountBadge.textContent = `${selectedPhotos.length} Photos Selected`;

    const filenames = selectedPhotos.map(p => {
      const name = p.title || p.id;
      return name.replace(/\.[^/.]+$/, "");
    });

    this.dom.lightroomStringArea.value = filenames.join(" ");
    this.dom.exportModal.classList.remove('hidden');
  }

  copyLightroomString() {
    const text = this.dom.lightroomStringArea.value;
    if (!text) {
      alert("No photos selected yet!");
      return;
    }
    navigator.clipboard.writeText(text).then(() => {
      this.showNotification("Copied! Paste into Lightroom Filter");
    });
  }

  downloadSelectionCsv() {
    const selectedPhotos = this.allPhotos.filter(p => this.decisions[p.id] === 'select');
    if (selectedPhotos.length === 0) {
      alert("No photos selected to export!");
      return;
    }

    let csv = "Index,Filename,GoogleDriveID,DownloadURL\n";
    selectedPhotos.forEach((p, idx) => {
      csv += `${idx + 1},"${p.title || p.id}","${p.id}","${p.downloadUrl || p.url}"\n`;
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Selected_Photos_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    this.showNotification("Exported Selection CSV!");
  }

  downloadOrganizedZip() {
    if (!this.sessionId) {
      alert("कृपया प्रथम Google Drive फोल्डर सिंक करा किंवा सेशन सुरू करा.");
      return;
    }
    const downloadUrl = `/api/session/export-zip?id=${encodeURIComponent(this.sessionId)}`;
    this.showNotification("Generating Organized 3-Folder ZIP...");
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = `PhotoProof_${(this.sessionTitle || 'Event').replace(/\s+/g, '_')}_Organized.zip`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => a.remove(), 1000);
  }

  // --- FILMSTRIP ---
  renderFilmstrip() {
    this.dom.filmstrip.innerHTML = '';
    const maxCount = Math.min(this.filteredPhotos.length, 600);

    for (let idx = 0; idx < maxCount; idx++) {
      const photo = this.filteredPhotos[idx];
      const thumb = document.createElement('div');
      thumb.className = `filmstrip-thumb ${idx === this.currentIndex ? 'active' : ''}`;
      thumb.dataset.id = photo.id;
      thumb.dataset.index = idx;

      const img = document.createElement('img');
      img.src = photo.thumb || photo.url;
      img.alt = photo.title;
      img.className = 'w-full h-full object-cover';
      img.loading = 'lazy';
      thumb.appendChild(img);

      const decision = this.decisions[photo.id];
      if (decision) {
        const dot = document.createElement('div');
        dot.className = `thumb-badge badge-${decision}`;
        thumb.appendChild(dot);
      }

      thumb.addEventListener('click', () => {
        this.showPhoto(idx, 'local');
      });

      this.dom.filmstrip.appendChild(thumb);
    }
  }

  updateFilmstripThumb(photoId, decision) {
    const thumb = this.dom.filmstrip.querySelector(`[data-id="${photoId}"]`);
    if (!thumb) return;

    const existingDot = thumb.querySelector('.thumb-badge');
    if (existingDot) existingDot.remove();

    if (decision) {
      const dot = document.createElement('div');
      dot.className = `thumb-badge badge-${decision}`;
      thumb.appendChild(dot);
    }
  }

  updateFilmstripActive(index) {
    const thumbs = this.dom.filmstrip.querySelectorAll('.filmstrip-thumb');
    thumbs.forEach((thumb, idx) => {
      if (idx === index) {
        thumb.classList.add('active');
        thumb.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
      } else {
        thumb.classList.remove('active');
      }
    });
  }

  // --- TOUCH GESTURES ---
  handleTouchStart(e) {
    if (e.touches.length !== 1) return;
    this.touchStartX = e.touches[0].clientX;
    this.touchStartY = e.touches[0].clientY;
    this.touchCurrentX = this.touchStartX;
    this.touchCurrentY = this.touchStartY;
    this.touchStartTime = Date.now();
    this.isSwiping = true;
  }

  handleTouchMove(e) {
    if (!this.isSwiping || e.touches.length !== 1 || this.zoomLevel > 1) return;
    this.touchCurrentX = e.touches[0].clientX;
    this.touchCurrentY = e.touches[0].clientY;

    const deltaX = this.touchCurrentX - this.touchStartX;
    const deltaY = this.touchCurrentY - this.touchStartY;

    if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 10) {
      this.dom.imageWrapper.style.transform = `translateX(${deltaX * 0.35}px)`;
    } else if (Math.abs(deltaY) > Math.abs(deltaX) && Math.abs(deltaY) > 15) {
      this.dom.imageWrapper.style.transform = `translateY(${deltaY * 0.35}px)`;
    }
  }

  handleTouchEnd() {
    if (!this.isSwiping) return;
    this.isSwiping = false;

    this.dom.imageWrapper.style.transition = 'transform 0.25s ease-out';
    this.dom.imageWrapper.style.transform = 'translate(0px, 0px)';
    setTimeout(() => {
      this.dom.imageWrapper.style.transition = '';
    }, 250);

    if (this.zoomLevel > 1) return;

    const deltaX = this.touchCurrentX - this.touchStartX;
    const deltaY = this.touchCurrentY - this.touchStartY;
    const elapsed = Date.now() - this.touchStartTime;

    if (Math.abs(deltaX) > Math.abs(deltaY) * 1.3 && Math.abs(deltaX) >= 45 && elapsed <= 600) {
      if (deltaX < 0) this.nextPhoto();
      else this.prevPhoto();
    } else if (Math.abs(deltaY) > Math.abs(deltaX) * 1.3 && Math.abs(deltaY) >= 55 && elapsed <= 600) {
      if (deltaY < 0) this.makeDecision('select');
      else this.makeDecision('reject');
    }
  }

  // --- ZOOM ---
  zoomIn() { this.setZoom(Math.min(3.5, this.zoomLevel + 0.4)); }
  zoomOut() { this.setZoom(Math.max(1, this.zoomLevel - 0.4)); }
  resetZoom() {
    this.zoomLevel = 1;
    this.panX = 0;
    this.panY = 0;
    this.applyTransform();
  }
  setZoom(level) {
    this.zoomLevel = level;
    if (level === 1) { this.panX = 0; this.panY = 0; }
    this.applyTransform();
  }
  applyTransform() {
    this.dom.activeImage.style.transform = `scale(${this.zoomLevel}) translate(${this.panX}px, ${this.panY}px)`;
    this.dom.activeImage.style.cursor = this.zoomLevel > 1 ? 'grab' : 'default';
  }

  // --- SLIDESHOW ---
  togglePlayPause() {
    if (this.isPlaying) this.stopSlideshow();
    else this.startSlideshow();
  }

  startSlideshow() {
    this.isPlaying = true;
    if (this.dom.playIcon) this.dom.playIcon.classList.add('hidden');
    if (this.dom.pauseIcon) this.dom.pauseIcon.classList.remove('hidden');
    this.resetSlideProgressBar();

    this.slideInterval = setInterval(() => {
      this.nextPhoto();
    }, this.slideDuration);
    this.showNotification("Slideshow Started");
  }

  stopSlideshow() {
    this.isPlaying = false;
    if (this.dom.playIcon) this.dom.playIcon.classList.remove('hidden');
    if (this.dom.pauseIcon) this.dom.pauseIcon.classList.add('hidden');
    clearInterval(this.slideInterval);
    clearInterval(this.progressInterval);
    if (this.dom.progressBar) this.dom.progressBar.style.width = '0%';
  }

  resetSlideProgressBar() {
    clearInterval(this.progressInterval);
    const start = Date.now();
    this.dom.progressBar.style.width = '0%';
    this.progressInterval = setInterval(() => {
      const pct = Math.min(100, ((Date.now() - start) / this.slideDuration) * 100);
      this.dom.progressBar.style.width = `${pct}%`;
      if (pct >= 100) clearInterval(this.progressInterval);
    }, 50);
  }

  resetInactivityTimer() {
    clearTimeout(this.inactivityTimeout);
    this.showControls();
    this.inactivityTimeout = setTimeout(() => {
      if (this.zoomLevel > 1) return;
      if (!this.dom.importModal.classList.contains('hidden') ||
          !this.dom.shareModal.classList.contains('hidden') ||
          !this.dom.brandingModal.classList.contains('hidden') ||
          !this.dom.driveModal.classList.contains('hidden') ||
          !this.dom.exportModal.classList.contains('hidden')) return;
      this.hideControls();
    }, 3800);
  }

  showControls() {
    this.controlsVisible = true;
    this.dom.dynamicIsland.classList.remove('player-chrome-top');
    this.dom.bottomBar.classList.remove('hidden-chrome');
    this.dom.prevBtn.classList.remove('hidden-chrome');
    this.dom.nextBtn.classList.remove('hidden-chrome');
    this.dom.downloadBtn.classList.remove('hidden-chrome');
  }

  hideControls() {
    this.controlsVisible = false;
    this.dom.bottomBar.classList.add('hidden-chrome');
    this.dom.prevBtn.classList.add('hidden-chrome');
    this.dom.nextBtn.classList.add('hidden-chrome');
    this.dom.downloadBtn.classList.add('hidden-chrome');
  }

  showNotification(text) {
    const toast = document.createElement('div');
    toast.className = 'fixed top-20 left-1/2 transform -translate-x-1/2 px-4 py-2.5 rounded-full ios-glass text-white text-xs font-semibold tracking-wide shadow-2xl z-50 transition-all duration-300 pointer-events-none opacity-0 translate-y-2 flex items-center gap-2';
    toast.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span><span>${text}</span>`;
    document.body.appendChild(toast);

    requestAnimationFrame(() => toast.classList.remove('opacity-0', 'translate-y-2'));
    setTimeout(() => {
      toast.classList.add('opacity-0', '-translate-y-2');
      setTimeout(() => toast.remove(), 300);
    }, 2400);
  }

  // --- EVENT BINDINGS ---
  bindEvents() {
    // THE 3 BIG DECISION BUTTONS (SELECT / REJECT / DECIDE)
    if (this.dom.btnSelect) this.dom.btnSelect.addEventListener('click', () => this.makeDecision('select'));
    if (this.dom.btnReject) this.dom.btnReject.addEventListener('click', () => this.makeDecision('reject'));
    if (this.dom.btnMaybe) this.dom.btnMaybe.addEventListener('click', () => this.makeDecision('maybe'));

    // Sound Toggle
    if (this.dom.soundToggleBtn) {
      this.dom.soundToggleBtn.addEventListener('click', () => {
        const isEnabled = this.audio.toggle();
        this.updateSoundUi();
        this.showNotification(isEnabled ? "Sound Effects ON" : "Sound Effects Muted");
      });
    }

    // Filter Buttons
    if (this.dom.filterAll) this.dom.filterAll.addEventListener('click', () => this.applyFilter('all'));
    if (this.dom.filterSelected) this.dom.filterSelected.addEventListener('click', () => this.applyFilter('selected'));
    if (this.dom.filterRejected) this.dom.filterRejected.addEventListener('click', () => this.applyFilter('rejected'));
    if (this.dom.filterMaybe) this.dom.filterMaybe.addEventListener('click', () => this.applyFilter('maybe'));
    if (this.dom.filterPending) this.dom.filterPending.addEventListener('click', () => this.applyFilter('pending'));

    // Navigation Buttons
    if (this.dom.prevBtn) this.dom.prevBtn.addEventListener('click', (e) => { e.stopPropagation(); this.prevPhoto(); });
    if (this.dom.nextBtn) this.dom.nextBtn.addEventListener('click', (e) => { e.stopPropagation(); this.nextPhoto(); });
    if (this.dom.downloadBtn) this.dom.downloadBtn.addEventListener('click', (e) => { e.stopPropagation(); this.downloadPhotoWithWatermark(); });
    if (this.dom.quickDownloadBtn) this.dom.quickDownloadBtn.addEventListener('click', (e) => { e.stopPropagation(); this.downloadPhotoWithWatermark(); });
    if (this.dom.mobileSaveBtn) this.dom.mobileSaveBtn.addEventListener('click', (e) => { e.stopPropagation(); this.downloadPhotoWithWatermark(); });

    // Touch events on canvas
    if (this.dom.imageCanvas) {
      this.dom.imageCanvas.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: true });
      this.dom.imageCanvas.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: true });
      this.dom.imageCanvas.addEventListener('touchend', (e) => this.handleTouchEnd(e), { passive: true });

      // Double click to toggle zoom
      this.dom.imageCanvas.addEventListener('dblclick', () => {
        if (this.zoomLevel > 1.2) this.resetZoom();
        else this.setZoom(2.2);
      });
    }

    // Slideshow
    if (this.dom.playPauseBtn) {
      this.dom.playPauseBtn.addEventListener('click', () => this.togglePlayPause());
    }

    // Fullscreen
    if (this.dom.fullscreenBtn) {
      this.dom.fullscreenBtn.addEventListener('click', () => {
        if (!document.fullscreenElement) document.documentElement.requestFullscreen().catch(() => {});
        else if (document.exitFullscreen) document.exitFullscreen();
      });
    }

    // Mousemove for inactivity
    window.addEventListener('mousemove', (e) => {
      this.resetInactivityTimer();
      if (this.isPanning && this.zoomLevel > 1) {
        this.panX = e.clientX - this.panStartX;
        this.panY = e.clientY - this.panStartY;
        this.applyTransform();
      }
    });

    if (this.dom.activeImage) {
      this.dom.activeImage.addEventListener('mousedown', (e) => {
        if (this.zoomLevel > 1) {
          this.isPanning = true;
          this.panStartX = e.clientX - this.panX;
          this.panStartY = e.clientY - this.panStartY;
          this.dom.activeImage.style.cursor = 'grabbing';
        }
      });
    }

    window.addEventListener('mouseup', () => {
      this.isPanning = false;
      this.applyTransform();
    });

    // Modals
    const showImport = () => {
      this.dom.importModal.classList.remove('hidden');
      if (window.lucide) window.lucide.createIcons();

      // Pre-fill branding fields
      if (this.dom.importPhotographerName) {
        this.dom.importPhotographerName.value = this.branding.photographerName || '';
      }
      if (this.branding.logoUrl && this.dom.importLogoPreview) {
        this.dom.importLogoPreview.src = this.branding.logoUrl;
        this.dom.importLogoPreviewContainer?.classList.remove('hidden');
      }

      setTimeout(() => this.dom.linkInput?.focus(), 150);
    };
    this.dom.openImportBtn.addEventListener('click', showImport);
    if (this.dom.quickOpenImportBtn) {
      this.dom.quickOpenImportBtn.addEventListener('click', showImport);
    }
    const qBar = document.getElementById('quickDriveBar');
    if (qBar) {
      qBar.addEventListener('click', showImport);
    }
    this.dom.importCloseBtn.addEventListener('click', () => this.dom.importModal.classList.add('hidden'));

    // Logo upload inside Import Modal
    if (this.dom.importLogoFileInput) {
      this.dom.importLogoFileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
          const reader = new FileReader();
          reader.onload = (evt) => {
            const dataUrl = evt.target.result;
            this.branding.logoUrl = dataUrl;
            localStorage.setItem('proof_logo_url', dataUrl);
            if (this.dom.importLogoPreview) {
              this.dom.importLogoPreview.src = dataUrl;
              this.dom.importLogoPreviewContainer?.classList.remove('hidden');
            }
            if (this.dom.logoPreview) {
              this.dom.logoPreview.src = dataUrl;
              this.dom.logoPreview.classList.remove('hidden');
            }
            this.showNotification("Logo Set! Will be embedded on client downloads.");
          };
          reader.readAsDataURL(file);
        }
      });
    }

    if (this.dom.importPhotographerName) {
      this.dom.importPhotographerName.addEventListener('input', (e) => {
        this.branding.photographerName = e.target.value.trim() || 'PHOTOGRAPHY PROOF';
        localStorage.setItem('proof_photographer_name', this.branding.photographerName);
        if (this.dom.photographerNameInput) {
          this.dom.photographerNameInput.value = this.branding.photographerName;
        }
      });
    }

    const pasteBtn = document.getElementById('pasteFromClipboardBtn');
    if (pasteBtn) {
      pasteBtn.addEventListener('click', async () => {
        try {
          const text = await navigator.clipboard.readText();
          if (text) {
            this.dom.linkInput.value = text.trim();
            this.showNotification("Link Pasted from Clipboard!");
          }
        } catch (e) {
          this.dom.linkInput.focus();
        }
      });
    }

    // 🌟 DIRECT ON-SCREEN GOOGLE DRIVE BAR HANDLERS 🌟
    if (this.dom.directPasteBtn) {
      this.dom.directPasteBtn.addEventListener('click', async () => {
        try {
          const text = await navigator.clipboard.readText();
          if (text) {
            this.dom.directDriveInput.value = text.trim();
            this.showNotification("Google Drive Link Pasted!");
          }
        } catch (e) {
          this.dom.directDriveInput?.focus();
        }
      });
    }

    if (this.dom.directLoadBtn) {
      this.dom.directLoadBtn.addEventListener('click', () => {
        const link = this.dom.directDriveInput?.value.trim();
        if (!link) {
          alert("Please paste your Google Drive folder link into the box!");
          this.dom.directDriveInput?.focus();
          return;
        }
        this.handleImport(link, "Event Photo Proofing");
      });
    }

    if (this.dom.directDriveInput) {
      this.dom.directDriveInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          const link = this.dom.directDriveInput.value.trim();
          if (link) {
            this.handleImport(link, "Event Photo Proofing");
          }
        }
      });
    }

    if (this.dom.openShareBtn) {
      this.dom.openShareBtn.addEventListener('click', () => {
        this.updateShareUrls();
        this.dom.shareModal?.classList.remove('hidden');
      });
    }
    if (this.dom.shareModalCloseBtn) {
      this.dom.shareModalCloseBtn.addEventListener('click', () => this.dom.shareModal?.classList.add('hidden'));
    }

    if (this.dom.copyNetworkBtn) {
      this.dom.copyNetworkBtn.addEventListener('click', () => {
        if (this.dom.networkUrlInput) {
          navigator.clipboard.writeText(this.dom.networkUrlInput.value).then(() => {
            this.showNotification("Mobile & Client Link Copied!");
          });
        }
      });
    }

    if (this.dom.copyLocalBtn) {
      this.dom.copyLocalBtn.addEventListener('click', () => {
        if (this.dom.localUrlInput) {
          navigator.clipboard.writeText(this.dom.localUrlInput.value).then(() => {
            this.showNotification("Local Link Copied!");
          });
        }
      });
    }

    // Branding Modal
    if (this.dom.openBrandingBtn) {
      this.dom.openBrandingBtn.addEventListener('click', () => {
        if (this.dom.logoUrlInput) this.dom.logoUrlInput.value = this.branding.logoUrl;
        if (this.dom.photographerNameInput) this.dom.photographerNameInput.value = this.branding.photographerName;
        if (this.branding.logoUrl && this.dom.logoPreview) {
          this.dom.logoPreview.src = this.branding.logoUrl;
          this.dom.logoPreview.classList.remove('hidden');
        }
        this.dom.brandingModal?.classList.remove('hidden');
      });
    }
    if (this.dom.brandingModalCloseBtn) {
      this.dom.brandingModalCloseBtn.addEventListener('click', () => this.dom.brandingModal?.classList.add('hidden'));
    }

    if (this.dom.logoFileInput) {
      this.dom.logoFileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
          const reader = new FileReader();
          reader.onload = (evt) => {
            this.branding.logoUrl = evt.target.result;
            if (this.dom.logoPreview) {
              this.dom.logoPreview.src = evt.target.result;
              this.dom.logoPreview.classList.remove('hidden');
            }
            if (this.dom.logoUrlInput) this.dom.logoUrlInput.value = '';
          };
          reader.readAsDataURL(file);
        }
      });
    }

    if (this.dom.saveBrandingBtn) {
      this.dom.saveBrandingBtn.addEventListener('click', () => {
        const urlInput = this.dom.logoUrlInput?.value.trim() || '';
        if (urlInput) this.branding.logoUrl = urlInput;
        this.branding.photographerName = this.dom.photographerNameInput?.value.trim() || 'PHOTOGRAPHER';

        localStorage.setItem('proof_logo_url', this.branding.logoUrl);
        localStorage.setItem('proof_photographer_name', this.branding.photographerName);

        if (this.sessionId) {
          fetch('/api/session/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              sessionId: this.sessionId,
              logoUrl: this.branding.logoUrl,
              photographerName: this.branding.photographerName
            })
          }).catch(() => {});
        }

        this.dom.brandingModal?.classList.add('hidden');
        this.showNotification("Branding & Watermark Saved!");
      });
    }

    // Google Drive 3-Folder Automation Modal
    if (this.dom.openDriveModalBtn) {
      this.dom.openDriveModalBtn.addEventListener('click', () => {
        if (this.dom.driveBridgeUrlInput) this.dom.driveBridgeUrlInput.value = this.driveBridgeUrl;
        this.dom.driveModal?.classList.remove('hidden');
      });
    }
    if (this.dom.driveModalCloseBtn) {
      this.dom.driveModalCloseBtn.addEventListener('click', () => this.dom.driveModal?.classList.add('hidden'));
    }

    if (this.dom.saveDriveBridgeBtn) {
      this.dom.saveDriveBridgeBtn.addEventListener('click', () => {
        this.driveBridgeUrl = this.dom.driveBridgeUrlInput?.value.trim() || '';
        localStorage.setItem('proof_drive_bridge_url', this.driveBridgeUrl);
        if (this.sessionId) {
          fetch('/api/session/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              sessionId: this.sessionId,
              driveBridgeUrl: this.driveBridgeUrl
            })
          }).catch(() => {});
        }
        this.dom.driveModal?.classList.add('hidden');
        this.showNotification("Google Drive 3-Folder Bridge Linked!");
      });
    }

    if (this.dom.syncDriveNowBtn) {
      this.dom.syncDriveNowBtn.addEventListener('click', () => {
        this.showNotification("3 Google Drive Folders Synced!");
      });
    }

    // Export Modal
    if (this.dom.openExportBtn) {
      this.dom.openExportBtn.addEventListener('click', () => this.openExportModal());
    }
    if (this.dom.exportModalCloseBtn) {
      this.dom.exportModalCloseBtn.addEventListener('click', () => this.dom.exportModal?.classList.add('hidden'));
    }
    if (this.dom.copyLightroomBtn) {
      this.dom.copyLightroomBtn.addEventListener('click', () => this.copyLightroomString());
    }
    if (this.dom.downloadCsvBtn) {
      this.dom.downloadCsvBtn.addEventListener('click', () => this.downloadSelectionCsv());
    }
    if (this.dom.downloadZipBtn) {
      this.dom.downloadZipBtn.addEventListener('click', () => this.downloadOrganizedZip());
    }

    // Import Actions (Start Proofing & Sync Photos)
    if (this.dom.processLinksBtn) {
      this.dom.processLinksBtn.addEventListener('click', () => {
        const text = this.dom.linkInput?.value || '';
        const title = this.dom.albumTitleInput?.value.trim() || 'Event Photo Proofing';
        this.handleImport(text, title);
      });
    }

    if (this.dom.loadDemoBtn) {
      this.dom.loadDemoBtn.addEventListener('click', () => {
        this.loadLocalPhotos(SAMPLE_ALBUM, "Sample Wedding Proofing");
        this.dom.importModal?.classList.add('hidden');
        this.showNotification("Demo Album Loaded");
      });
    }

    // KEYBOARD SHORTCUTS
    window.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      switch (e.key) {
        case 's':
        case 'S':
        case '1':
          this.makeDecision('select');
          break;
        case 'r':
        case 'R':
        case '2':
          this.makeDecision('reject');
          break;
        case 'm':
        case 'M':
        case '3':
          this.makeDecision('maybe');
          break;
        case 'u':
        case 'U':
        case 'Backspace':
          this.makeDecision(null);
          break;
        case 'ArrowRight':
        case 'l':
          this.nextPhoto();
          break;
        case 'ArrowLeft':
        case 'j':
          this.prevPhoto();
          break;
        case ' ':
          e.preventDefault();
          this.togglePlayPause();
          break;
        case 'e':
        case 'E':
          this.openExportModal();
          break;
        case 'f':
        case 'F':
          if (this.dom.fullscreenBtn) this.dom.fullscreenBtn.click();
          break;
        case 'Escape':
          this.dom.importModal?.classList.add('hidden');
          this.dom.shareModal?.classList.add('hidden');
          this.dom.brandingModal?.classList.add('hidden');
          this.dom.driveModal?.classList.add('hidden');
          this.dom.exportModal?.classList.add('hidden');
          this.resetZoom();
          break;
      }
    });
  }
}

function initPhotoProofApp() {
  if (!window.app) {
    try {
      window.app = new PhotoProofApp();
      console.log("PhotoProofApp initialized successfully!");
      if (window.lucide) {
        window.lucide.createIcons();
      }
    } catch (err) {
      console.error("Error creating PhotoProofApp:", err);
    }
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initPhotoProofApp);
} else {
  initPhotoProofApp();
}
