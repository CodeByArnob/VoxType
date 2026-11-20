/**
 * VoxType Official Website Scripts
 * Interactive Push-to-Talk Playground, Lightbox, Tab Controls & Accordions
 */

document.addEventListener('DOMContentLoaded', () => {
  initMobileNav();
  initCopyButtons();
  initInteractivePlayground();
  initScreenshotGallery();
  initInstallTabs();
  initFaqAccordion();
});

/* --------------------------------------------------------------------------
   Mobile Navigation Drawer
   -------------------------------------------------------------------------- */
function initMobileNav() {
  const toggle = document.querySelector('.menu-toggle');
  const menu = document.querySelector('.nav-menu');
  if (!toggle || !menu) return;

  toggle.addEventListener('click', () => {
    const isOpen = menu.classList.toggle('open');
    toggle.setAttribute('aria-expanded', isOpen);
  });

  menu.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      menu.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    });
  });
}

/* --------------------------------------------------------------------------
   Copy-to-Clipboard Utilities
   -------------------------------------------------------------------------- */
function initCopyButtons() {
  document.querySelectorAll('[data-copy]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const text = btn.getAttribute('data-copy');
      if (!text) return;

      try {
        await navigator.clipboard.writeText(text);
        const originalText = btn.innerHTML;
        btn.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
          <span style="color:#10B981;">Copied!</span>
        `;
        setTimeout(() => {
          btn.innerHTML = originalText;
        }, 1800);
      } catch (err) {
        console.error('Clipboard copy failed:', err);
      }
    });
  });
}

/* --------------------------------------------------------------------------
   Interactive Voice Typing Playground / Simulator
   -------------------------------------------------------------------------- */
function initInteractivePlayground() {
  const trigger = document.getElementById('simMicTrigger');
  const statusLbl = document.getElementById('simStatusLbl');
  const metricsTag = document.getElementById('simMetricsTag');
  const editor = document.getElementById('simEditorContent');
  if (!trigger || !statusLbl || !editor) return;

  const sampleTexts = [
    "VoxType transcribes spoken words with sub-second latency into any active window.",
    "Holding Left Ctrl starts voice recording instantly without window switching.",
    "Offline Faster-Whisper inference guarantees complete privacy with zero cloud dependencies.",
    "Native SendInput injects Unicode characters directly at your cursor position."
  ];

  let sampleIndex = 0;
  let isRecording = false;
  let timerInterval = null;
  let secondsElapsed = 0;

  function startRecording() {
    if (isRecording) return;
    isRecording = true;
    secondsElapsed = 0;
    trigger.classList.add('active');
    statusLbl.innerHTML = '<span style="color:#EF4444;">● Listening...</span> speak now (recording float32 16kHz audio)';
    metricsTag.textContent = "REC: 00:00";

    timerInterval = setInterval(() => {
      secondsElapsed++;
      const s = secondsElapsed < 10 ? '0' + secondsElapsed : secondsElapsed;
      metricsTag.textContent = `REC: 00:${s}`;
    }, 1000);
  }

  function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    clearInterval(timerInterval);
    trigger.classList.remove('active');

    statusLbl.innerHTML = '<span style="color:#38BDF8;">⚡ Transcribing speech locally with Faster-Whisper...</span>';
    metricsTag.textContent = "Inference...";

    setTimeout(() => {
      const textToType = sampleTexts[sampleIndex % sampleTexts.length];
      sampleIndex++;
      typeText(textToType, () => {
        statusLbl.innerHTML = '<span style="color:#10B981;">✓ Injected directly at active cursor!</span>';
        const ms = Math.floor(Math.random() * 80) + 280;
        metricsTag.textContent = `⚡ ${ms}ms inference • 0 bytes uploaded`;
      });
    }, 380);
  }

  function typeText(fullText, callback) {
    editor.innerHTML = '';
    let i = 0;
    const interval = setInterval(() => {
      if (i < fullText.length) {
        editor.innerHTML = fullText.substring(0, i + 1) + '<span class="sim-cursor"></span>';
        i++;
      } else {
        clearInterval(interval);
        editor.innerHTML = fullText + ' <span class="sim-cursor"></span>';
        if (callback) callback();
      }
    }, 22);
  }

  // Pointer / Mouse events
  trigger.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    startRecording();
  });

  window.addEventListener('pointerup', () => {
    if (isRecording) stopRecording();
  });

  // Keyboard controls when focused
  window.addEventListener('keydown', (e) => {
    if ((e.code === 'Space' || e.code === 'ControlLeft') && document.activeElement === trigger) {
      e.preventDefault();
      startRecording();
    }
  });

  window.addEventListener('keyup', (e) => {
    if ((e.code === 'Space' || e.code === 'ControlLeft') && isRecording) {
      e.preventDefault();
      stopRecording();
    }
  });
}

/* --------------------------------------------------------------------------
   Screenshot Gallery & Modal Lightbox
   -------------------------------------------------------------------------- */
function initScreenshotGallery() {
  const tabs = document.querySelectorAll('.gallery-tab-btn');
  const stageImg = document.getElementById('galleryStageImg');
  const captionTitle = document.getElementById('galleryCaptionTitle');
  const captionDesc = document.getElementById('galleryCaptionDesc');
  const lightbox = document.getElementById('modalLightbox');
  const lightboxImg = document.getElementById('lightboxImg');
  const closeBtn = document.getElementById('modalCloseBtn');
  if (!stageImg || !tabs.length) return;

  const screens = {
    main: {
      src: './images/01_main_idle.png',
      title: 'Main Voice Typing Interface',
      desc: 'Focused desktop view with 60 FPS animated microphone, real-time waveform, and session metrics.'
    },
    recording: {
      src: './images/02_main_recording.png',
      title: 'Active Push-to-Talk Recording',
      desc: 'Real-time multi-bar waveform visualizer reflecting live 16kHz microphone audio energy.'
    },
    transcribed: {
      src: './images/04_main_transcribed.png',
      title: 'Completed Transcription & Session History',
      desc: 'Local recovery log with measured inference speed (384ms) and non-destructive clipboard copy.'
    },
    models: {
      src: './images/05_models_manager.png',
      title: 'Faster-Whisper Model Variants',
      desc: 'Download, switch, and delete models (Tiny, Base, Small, Medium, Large) with hardware CPU profiling.'
    },
    audio: {
      src: './images/06_audio_devices.png',
      title: 'Microphone Selection & Live VU Meter',
      desc: 'Calibrate microphone input levels, verify OS permissions, and configure sound feedback chimes.'
    },
    shortcuts: {
      src: './images/07_shortcuts_config.png',
      title: 'Global Keyboard Shortcuts Pad',
      desc: 'Physical Left Ctrl discrimination (VK_LCONTROL = 162), Hold-to-Talk vs Toggle-to-Talk, and conflict detection.'
    },
    formatting: {
      src: './images/08_formatting_rules.png',
      title: 'Formatting Rules & Custom Shortcuts',
      desc: 'Punctuation auto-cleanup, filler word filter ("um", "uh"), and custom phrase-to-emoji expansions.'
    },
    settings: {
      src: './images/09_settings_about.png',
      title: 'Settings, Retention Privacy & About',
      desc: 'Strict zero-retention mode, theme selection, tray behavior, and open source MIT metadata.'
    },
    floating: {
      src: './images/10_floating_indicator_listening.png',
      title: 'Compact Floating Indicator Overlay',
      desc: 'Non-activating overlay pill with animated audio waves and real-time recording timer.'
    }
  };

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const key = tab.getAttribute('data-screen');
      const item = screens[key];
      if (!item) return;

      stageImg.style.opacity = '0';
      setTimeout(() => {
        stageImg.src = item.src;
        stageImg.alt = item.title;
        if (captionTitle) captionTitle.textContent = item.title;
        if (captionDesc) captionDesc.textContent = item.desc;
        stageImg.style.opacity = '1';
      }, 150);
    });
  });

  // Lightbox opening
  stageImg.addEventListener('click', () => {
    if (!lightbox || !lightboxImg) return;
    lightboxImg.src = stageImg.src;
    lightboxImg.alt = stageImg.alt;
    lightbox.classList.add('open');
    document.body.style.overflow = 'hidden';
  });

  function closeLightbox() {
    if (!lightbox) return;
    lightbox.classList.remove('open');
    document.body.style.overflow = '';
  }

  if (closeBtn) closeBtn.addEventListener('click', closeLightbox);
  if (lightbox) {
    lightbox.addEventListener('click', (e) => {
      if (e.target === lightbox) closeLightbox();
    });
  }
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && lightbox && lightbox.classList.contains('open')) {
      closeLightbox();
    }
  });
}

/* --------------------------------------------------------------------------
   Installation Tabs
   -------------------------------------------------------------------------- */
function initInstallTabs() {
  const tabBtns = document.querySelectorAll('.install-tab-btn');
  const panels = document.querySelectorAll('.install-panel');
  if (!tabBtns.length || !panels.length) return;

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetId = btn.getAttribute('data-tab');
      const panel = document.getElementById(targetId);
      if (panel) panel.classList.add('active');
    });
  });
}

/* --------------------------------------------------------------------------
   FAQ Accordion
   -------------------------------------------------------------------------- */
function initFaqAccordion() {
  const items = document.querySelectorAll('.faq-item');
  items.forEach(item => {
    const question = item.querySelector('.faq-question');
    if (!question) return;

    question.addEventListener('click', () => {
      const isOpen = item.classList.contains('open');
      items.forEach(i => i.classList.remove('open'));
      if (!isOpen) item.classList.add('open');
    });
  });
}
