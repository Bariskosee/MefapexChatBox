# MEFAPEX ChatBox - Accessibility & Theme Features

## Overview
This document outlines the accessibility improvements and theme features implemented in the MEFAPEX ChatBox application.

## ✨ New Features

### 🎨 Theme System
- **Light/Dark Theme Toggle**: Users can switch between light and dark themes
- **Per-User Theme Persistence**: Theme preferences are saved per user
- **System Theme Detection**: Automatically detects user's system preference
- **Smooth Transitions**: Animated theme switching with CSS variables

### ♿ Accessibility Improvements

#### ARIA Support
- **Semantic HTML**: Proper use of `section`, `aside`, `main`, and other semantic elements
- **ARIA Roles**: Added appropriate roles like `listitem`, `log`, `status`, etc.
- **ARIA Labels**: Descriptive labels for all interactive elements
- **Live Regions**: Real-time announcements for screen readers

#### Keyboard Navigation
- **Tab Navigation**: Full keyboard accessibility with proper tab order
- **Focus Management**: Visual focus indicators and focus trapping in modals
- **Keyboard Shortcuts**:
  - `Enter` - Send message or activate buttons
  - `Escape` - Close sidebar or focus message input
  - `Tab/Shift+Tab` - Navigate between elements
  - `Ctrl+F1` - Show keyboard shortcuts help

#### Screen Reader Support
- **Message Announcements**: New messages are announced to screen readers
- **Status Updates**: Login/logout and theme changes are announced
- **Descriptive Labels**: All buttons and inputs have descriptive labels
- **Skip Links**: Quick navigation to main content

### 📱 Enhanced UX
- **Touch Target Size**: All interactive elements meet 44px minimum size
- **High Contrast Support**: Improved colors for high contrast mode
- **Reduced Motion**: Respects user's motion preferences
- **Error Handling**: Better error messages with screen reader support

## 🏗️ Technical Implementation

### File Structure
```
static/
├── index.html              # Main HTML with semantic markup
├── styles.css              # Base styles with CSS variables
├── themes.css              # Theme system and CSS variables
├── theme-manager.js        # Theme switching logic
├── accessibility.js        # Accessibility enhancements
├── script.js              # Main application logic (enhanced)
├── index-handlers.js      # Event handlers (enhanced)
└── ...
```

### CSS Variables System
The theme system uses CSS custom properties for consistent theming:

```css
[data-theme="dark"] {
    --primary-bg: /* dark gradients */
    --text-primary: #ecf0f1;
    --button-primary: /* blue gradient */
    /* ... more variables */
}

[data-theme="light"] {
    --primary-bg: /* light gradients */
    --text-primary: #212529;
    --button-primary: /* blue gradient */
    /* ... more variables */
}
```

### JavaScript Modules

#### ThemeManager
```javascript
class ThemeManager {
    loadThemePreference()     // Load user/global theme
    saveThemePreference()     // Save theme choice
    toggleTheme()            // Switch between themes
    refreshForUser()         // Refresh on user change
}
```

#### AccessibilityManager
```javascript
class AccessibilityManager {
    setupKeyboardNavigation() // Keyboard event handling
    enableFocusTrap()         // Modal focus management
    announceMessage()         // Screen reader announcements
    updateMessageCount()      // Live region updates
}
```

## 🚀 Usage

### Theme Switching
1. Click the theme toggle button (☀️/🌙) in the header
2. Theme preference is automatically saved per user
3. Themes persist across browser sessions

### Keyboard Navigation
1. Use `Tab` to navigate between elements
2. Use `Enter` or `Space` to activate buttons
3. Use `Escape` to close modals or return to main content
4. Message input is always accessible via `Escape` key

### Screen Reader Support
- All content is properly labeled and announced
- Message history is read as a live log
- Status changes are announced automatically
- Error messages are announced immediately

## 🔧 Configuration

### Theme Preferences
Themes are stored in localStorage with fallbacks:
1. User-specific: `mefapex_theme_${user_id}`
2. Global: `mefapex_theme`
3. System preference via `prefers-color-scheme`

### Accessibility Settings
- Respects `prefers-reduced-motion` for animations
- Supports `prefers-contrast: high` for better visibility
- Focus indicators only show during keyboard navigation

## 🧪 Testing

### Accessibility Testing
- Test with screen readers (NVDA, JAWS, VoiceOver)
- Verify keyboard-only navigation
- Check color contrast ratios
- Test with reduced motion preferences

### Theme Testing
- Verify theme persistence across sessions
- Test theme switching during active chat
- Check CSS variable fallbacks
- Test system theme detection

## 📝 Browser Support
- **Modern browsers**: Full support for CSS variables and accessibility features
- **IE11**: Basic fallback support (graceful degradation)
- **Mobile**: Touch-optimized with proper touch targets

## 🔄 Migration Notes
Existing users will:
- Keep their current session state
- Get dark theme by default (existing behavior)
- Benefit from improved accessibility immediately
- See smooth transitions when switching themes

## 🐛 Known Issues
- None currently identified

## 📚 References
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [CSS Custom Properties](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)
