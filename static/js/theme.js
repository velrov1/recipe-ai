// Enhanced Theme toggle functionality for RecipAI

document.addEventListener('DOMContentLoaded', () => {
  // Check for saved theme preference or use system preference
  const savedTheme = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  
  // Set initial theme
  if (savedTheme) {
    document.documentElement.setAttribute('data-theme', savedTheme);
  } else if (prefersDark) {
    document.documentElement.setAttribute('data-theme', 'dark');
    localStorage.setItem('theme', 'dark');
  }
  
  // Helper function to get current theme
  function getCurrentTheme() {
    return document.documentElement.getAttribute('data-theme') || 'light';
  }
  
  // Create theme toggle button with animation
  // Removed theme toggle button as requested
  // createThemeToggle();
});

// Helper function to get current theme
function getCurrentTheme() {
  return document.documentElement.getAttribute('data-theme') || 'light';
}

// Create enhanced theme toggle button
function createThemeToggle() {
  const themeToggle = document.createElement('button');
  themeToggle.className = 'theme-toggle';
  themeToggle.setAttribute('aria-label', 'Toggle dark mode');
  
  // Create inner elements for better animation
  const moonIcon = document.createElement('i');
  moonIcon.className = 'fas fa-moon';
  moonIcon.style.position = 'absolute';
  moonIcon.style.transition = 'all 0.3s ease';
  
  const sunIcon = document.createElement('i');
  sunIcon.className = 'fas fa-sun';
  sunIcon.style.position = 'absolute';
  sunIcon.style.transition = 'all 0.3s ease';
  
  // Append icons to button
  themeToggle.appendChild(moonIcon);
  themeToggle.appendChild(sunIcon);
  
  // Set initial state
  updateThemeToggleState(themeToggle);
  
  // Add toggle button to the DOM
  document.body.appendChild(themeToggle);
  
  // Toggle theme function with animation
  themeToggle.addEventListener('click', () => {
    // Add click effect
    themeToggle.classList.add('theme-toggle-clicked');
    setTimeout(() => {
      themeToggle.classList.remove('theme-toggle-clicked');
    }, 300);
    
    const currentTheme = getCurrentTheme();
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    // Update theme with transition
    document.body.style.transition = 'background-color 0.5s ease, color 0.5s ease';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    // Update button icon with animation
    updateThemeToggleState(themeToggle);
    
    // Announce theme change for screen readers
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', 'polite');
    announcement.classList.add('sr-only');
    announcement.textContent = `Theme changed to ${newTheme} mode`;
    document.body.appendChild(announcement);
    setTimeout(() => announcement.remove(), 3000);
  });
}

// Update theme toggle button state
function updateThemeToggleState(themeToggle) {
  const currentTheme = getCurrentTheme();
  const moonIcon = themeToggle.querySelector('.fa-moon');
  const sunIcon = themeToggle.querySelector('.fa-sun');
  
  if (currentTheme === 'dark') {
    moonIcon.style.opacity = '0';
    moonIcon.style.transform = 'rotate(-30deg) scale(0.5)';
    sunIcon.style.opacity = '1';
    sunIcon.style.transform = 'rotate(0) scale(1)';
    themeToggle.style.backgroundColor = '#334155';
    themeToggle.style.borderColor = '#475569';
  } else {
    moonIcon.style.opacity = '1';
    moonIcon.style.transform = 'rotate(0) scale(1)';
    sunIcon.style.opacity = '0';
    sunIcon.style.transform = 'rotate(30deg) scale(0.5)';
    themeToggle.style.backgroundColor = '#f1f5f9';
    themeToggle.style.borderColor = '#e2e8f0';
  }
}

// Add this to CSS via JavaScript to avoid modifying the CSS file again
const styleElement = document.createElement('style');
styleElement.textContent = `
  .theme-toggle {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 100;
    width: 44px;
    height: 44px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 4px 8px var(--shadow-color);
    transition: all 0.3s ease;
    border: 1px solid var(--border-color);
  }
  
  .theme-toggle:hover {
    transform: scale(1.1);
    box-shadow: 0 6px 12px var(--shadow-color);
  }
  
  .theme-toggle-clicked {
    animation: pulse 0.3s ease-in-out;
  }
  
  @keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(0.9); }
    100% { transform: scale(1); }
  }
  
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border-width: 0;
  }
`;

document.head.appendChild(styleElement);