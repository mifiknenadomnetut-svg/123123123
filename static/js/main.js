// TypeRace — main.js
// Most page logic lives inline in templates.
// This file handles shared utilities.

// Auto-dismiss flash messages
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => el.style.opacity = '0', 3000);
    setTimeout(() => el.remove(), 3400);
    el.style.transition = 'opacity 0.4s';
  });
});
