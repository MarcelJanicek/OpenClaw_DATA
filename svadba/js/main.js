// =============================================
// MARCEL & BIBIANA WEDDING — JS
// =============================================

// ---- ENVELOPE INTRO ----
function openEnvelope() {
  const wrap    = document.getElementById('env-wrap');
  const overlay = document.getElementById('env-overlay');
  wrap.classList.add('opening');
  setTimeout(() => overlay.classList.add('fade-out'), 1000);
  setTimeout(() => {
    overlay.style.display = 'none';
    document.body.style.overflow = '';
  }, 2400);
}
document.body.style.overflow = 'hidden';

// ---- COUNTDOWN ----
function updateCountdown() {
  const wedding = new Date('2026-09-19T14:00:00');
  const now = new Date();
  const diff = wedding - now;

  if (diff <= 0) {
    document.getElementById('countdown').innerHTML =
      '<p style="color:rgba(255,255,255,0.8);font-size:1.2rem;letter-spacing:0.1em;">Dnes je náš deň! 🤍</p>';
    return;
  }

  const days    = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours   = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  const seconds = Math.floor((diff % (1000 * 60)) / 1000);

  document.getElementById('cd-days').textContent    = String(days).padStart(2,'0');
  document.getElementById('cd-hours').textContent   = String(hours).padStart(2,'0');
  document.getElementById('cd-minutes').textContent = String(minutes).padStart(2,'0');
  document.getElementById('cd-seconds').textContent = String(seconds).padStart(2,'0');
}

updateCountdown();
setInterval(updateCountdown, 1000);

// ---- NAVBAR SCROLL ----
window.addEventListener('scroll', () => {
  const nav = document.getElementById('navbar');
  if (window.scrollY > 50) {
    nav.classList.add('scrolled');
  } else {
    nav.classList.remove('scrolled');
  }
});

// ---- MOBILE NAV ----
function toggleNav() {
  const m = document.getElementById('navMobile');
  m.classList.toggle('open');
}

// ---- SMOOTH SCROLL for nav links ----
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function(e) {
    const target = document.querySelector(this.getAttribute('href'));
    if (target) {
      e.preventDefault();
      const offset = 64;
      const top = target.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top, behavior: 'smooth' });
    }
  });
});

// ---- RSVP FORM ----
function submitRSVP(e) {
  e.preventDefault();

  const form = document.getElementById('rsvpForm');
  const data = new FormData(form);
  const payload = {};

  data.forEach((val, key) => {
    if (payload[key]) {
      if (!Array.isArray(payload[key])) payload[key] = [payload[key]];
      payload[key].push(val);
    } else {
      payload[key] = val;
    }
  });

  // Collect checkboxes manually
  const checked = [...form.querySelectorAll('input[name="jedlo"]:checked')]
    .map(c => c.value);
  payload.jedlo = checked;

  // Save to localStorage (local backup)
  const responses = JSON.parse(localStorage.getItem('rsvp_responses') || '[]');
  responses.push({ ...payload, timestamp: new Date().toISOString() });
  localStorage.setItem('rsvp_responses', JSON.stringify(responses));

  // TODO: Send to backend / Formspree / Netlify Forms
  // Replace ACTION_URL with your form endpoint:
  // fetch('ACTION_URL', {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify(payload)
  // });

  // Show success
  form.style.display = 'none';
  document.getElementById('rsvpSuccess').style.display = 'block';

  console.log('RSVP submitted:', payload);
}

// ---- SCROLL ANIMATIONS ----
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = '1';
      entry.target.style.transform = 'translateY(0)';
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.story-item, .tl-item, .accom-card, .venue-info').forEach(el => {
  el.style.opacity = '0';
  el.style.transform = 'translateY(20px)';
  el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
  observer.observe(el);
});
