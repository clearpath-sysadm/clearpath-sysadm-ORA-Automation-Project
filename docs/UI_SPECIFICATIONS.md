# UI Specifications - Oracare Fulfillment System

**Document Version:** 1.0.0  
**Last Updated:** November 3, 2025  
**Status:** Active  
**Format:** Based on [Keep a Changelog](https://keepachangelog.com/) and industry best practices

---

## Document Purpose

This UI Specification defines the visual design, interaction patterns, component library, and user interface standards for the Oracare Fulfillment System. It serves as the authoritative reference for implementing and maintaining consistent UI/UX across all pages and features.

**Audience:** Developers, Designers, QA Engineers, Product Managers

---

## Table of Contents

1. [Design System](#design-system)
2. [Component Library](#component-library)
3. [Page Specifications](#page-specifications)
4. [Interaction Patterns](#interaction-patterns)
5. [Responsive Design](#responsive-design)
6. [Accessibility](#accessibility)
7. [Edge Cases & Error States](#edge-cases--error-states)

---

## Design System

### Color Palette

#### Primary Colors
```css
--primary-blue: #2B7DE9      /* Oracare brand blue - primary actions, links */
--deep-navy: #1B2A4A         /* Headers, navigation, emphasis */
--accent-blue: #1E40AF       /* Hover states, active elements */
```

#### Neutral Colors
```css
--text-primary: #111827      /* Body text, headings */
--text-secondary: #6B7280    /* Subtext, labels */
--text-tertiary: #9CA3AF     /* Disabled text, placeholders */
--bg-primary: #FFFFFF        /* Main background */
--bg-secondary: #F9FAFB      /* Section backgrounds */
--bg-tertiary: #F3F4F6       /* Subtle backgrounds */
--border-color: #E5E7EB      /* Borders, dividers */
```

#### Semantic Colors
```css
--success: #10B981           /* Success states, positive actions */
--warning: #F59E0B           /* Warnings, attention needed */
--danger: #EF4444            /* Errors, destructive actions */
--info: #3B82F6              /* Informational messages */
```

#### Light/Dark Mode
- **Light Mode:** Default, white backgrounds, dark text
- **Dark Mode:** Dark navy sidebar (#1B2A4A) with glass effect, maintains readability contrast

### Typography

#### Font Families
```css
--font-body: 'IBM Plex Sans', -apple-system, system-ui, sans-serif;
--font-hero: 'Source Serif 4', Georgia, serif;  /* Stats, hero numbers only */
--font-mono: 'SF Mono', 'Monaco', 'Consolas', monospace;  /* Code, IDs */
```

#### Type Scale
```css
--font-xs: 0.75rem (12px)    /* Small labels, metadata */
--font-sm: 0.875rem (14px)   /* Body text, table cells */
--font-base: 1rem (16px)     /* Default body text */
--font-lg: 1.125rem (18px)   /* Subheadings */
--font-xl: 1.25rem (20px)    /* Card headers */
--font-2xl: 1.5rem (24px)    /* Section titles */
--font-3xl: 1.875rem (30px)  /* Page headers */
--font-4xl: 2.25rem (36px)   /* Hero stats */
```

#### Font Weights
- **Regular (400):** Body text, descriptions
- **Medium (500):** Labels, table headers
- **Semibold (600):** Buttons, emphasis
- **Bold (700):** Page titles, headers

### Spacing System

```css
--spacing-xs: 0.25rem (4px)
--spacing-sm: 0.5rem (8px)
--spacing-md: 1rem (16px)
--spacing-lg: 1.5rem (24px)
--spacing-xl: 2rem (32px)
--spacing-2xl: 3rem (48px)
```

### Elevation & Shadows

```css
--shadow-sm: 0 1px 2px rgba(0,0,0,0.05);              /* Subtle elevation */
--shadow-md: 0 4px 6px rgba(0,0,0,0.07);              /* Cards, dropdowns */
--shadow-lg: 0 10px 15px rgba(0,0,0,0.1);             /* Modals, popovers */
--shadow-xl: 0 20px 25px rgba(0,0,0,0.15);            /* High priority overlays */
--shadow-glass: 0 8px 32px rgba(27,42,74,0.12);       /* Glass effect */
```

### Border Radius

```css
--radius-sm: 0.25rem (4px)   /* Small elements */
--radius-md: 0.5rem (8px)    /* Buttons, inputs */
--radius-lg: 0.75rem (12px)  /* Cards */
--radius-xl: 1rem (16px)     /* Large containers */
--radius-full: 9999px        /* Pills, badges */
```

---

## Component Library

### Buttons

#### Primary Button
```html
<button class="btn-primary">
  Save Changes
</button>
```
**Visual Specs:**
- Background: `var(--primary-blue)`
- Text: White, font-weight 600
- Padding: 12px 24px
- Border-radius: `var(--radius-md)`
- Shadow: `var(--shadow-sm)`
- **Hover:** Darken background by 10%, lift with `var(--shadow-md)`
- **Active:** Slight scale (0.98)
- **Disabled:** 50% opacity, cursor not-allowed

#### Secondary Button
```html
<button class="btn-secondary">
  Cancel
</button>
```
**Visual Specs:**
- Background: White
- Border: 1px solid `var(--border-color)`
- Text: `var(--text-primary)`
- **Hover:** Background `var(--bg-secondary)`

#### Danger Button
```html
<button class="btn-danger">
  Delete Order
</button>
```
**Visual Specs:**
- Background: `var(--danger)`
- Text: White
- **Hover:** Darken to #DC2626

### Cards

```html
<div class="card">
  <div class="card-header">
    <h3>Card Title</h3>
  </div>
  <div class="card-body">
    Content here
  </div>
</div>
```

**Visual Specs:**
- Background: White
- Border: 1px solid `var(--border-color)`
- Border-radius: `var(--radius-lg)`
- Padding: 24px
- Shadow: `var(--shadow-sm)`
- **Hover:** Lift to `var(--shadow-md)` (interactive cards only)

### Status Badges

```html
<span class="status-badge status-shipped">Shipped</span>
<span class="status-badge status-pending">Pending</span>
<span class="status-badge status-cancelled">Cancelled</span>
```

**Visual Specs:**
- Padding: 4px 12px
- Border-radius: `var(--radius-full)`
- Font-size: `var(--font-xs)`
- Font-weight: 600
- Text-transform: Uppercase
- Letter-spacing: 0.05em

**Status Colors:**
- **Shipped:** Green background (#D1FAE5), green text (#065F46)
- **Pending:** Yellow background (#FEF3C7), yellow text (#92400E)
- **Cancelled:** Red background (#FEE2E2), red text (#991B1B)
- **On Hold:** Gray background (#F3F4F6), gray text (#374151)

### Tables

```html
<table class="data-table">
  <thead>
    <tr>
      <th>Column 1</th>
      <th>Column 2</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Data 1</td>
      <td>Data 2</td>
    </tr>
  </tbody>
</table>
```

**Visual Specs:**
- Width: 100%
- Border-collapse: collapse
- **Header:** Background `var(--bg-secondary)`, font-weight 600, padding 12px
- **Cells:** Padding 12px, border-bottom 1px solid `var(--border-color)`
- **Row Hover:** Background `var(--bg-tertiary)`
- **Alternating Rows:** Optional zebra striping with `var(--bg-secondary)`

### Modals

```html
<div class="modal-overlay">
  <div class="modal">
    <div class="modal-header">
      <h2>Modal Title</h2>
      <button class="modal-close">×</button>
    </div>
    <div class="modal-body">
      Content
    </div>
    <div class="modal-footer">
      <button class="btn-secondary">Cancel</button>
      <button class="btn-primary">Confirm</button>
    </div>
  </div>
</div>
```

**Visual Specs:**
- **Overlay:** Semi-transparent black (rgba(0,0,0,0.5)), backdrop-blur 4px
- **Modal:** White background, max-width 600px, border-radius `var(--radius-xl)`
- **Shadow:** `var(--shadow-xl)`
- **Animation:** Fade in + scale from 0.95 to 1.0 over 200ms
- **Close Button:** Size 32px, hover background `var(--bg-tertiary)`

### Forms

#### Text Input
```html
<div class="form-group">
  <label for="orderNumber">Order Number</label>
  <input type="text" id="orderNumber" class="form-input" placeholder="Enter order number">
  <span class="form-help">6-digit order number</span>
</div>
```

**Visual Specs:**
- Padding: 10px 14px
- Border: 1px solid `var(--border-color)`
- Border-radius: `var(--radius-md)`
- **Focus:** Border `var(--primary-blue)`, shadow 0 0 0 3px rgba(43,125,233,0.1)
- **Error:** Border `var(--danger)`, red focus shadow
- **Disabled:** Background `var(--bg-tertiary)`, cursor not-allowed

#### Select Dropdown
```html
<select class="form-select">
  <option>Option 1</option>
  <option>Option 2</option>
</select>
```

**Visual Specs:**
- Same as text input
- Chevron icon right-aligned
- Dropdown shadow `var(--shadow-lg)`

### Navigation

#### Sidebar
```html
<nav class="sidebar">
  <div class="sidebar-header">
    <img src="logo.png" alt="Oracare">
  </div>
  <ul class="sidebar-nav">
    <li class="nav-item active">
      <a href="/">Dashboard</a>
    </li>
    <li class="nav-item">
      <a href="/inventory">Inventory</a>
    </li>
  </ul>
</nav>
```

**Visual Specs:**
- Width: 240px (desktop), 100% (mobile collapsed)
- Background: Deep navy (#1B2A4A) with glass effect
- **Glass Effect:** backdrop-filter blur(10px), semi-transparent overlay
- **Active Item:** Blue left border (4px), lighter background
- **Hover:** Subtle background lightening
- **Logo:** 32px height, 16px top/bottom margin

#### Top Navigation Bar
```html
<header class="top-nav">
  <div class="nav-left">
    <h1>Page Title</h1>
  </div>
  <div class="nav-right">
    <button class="user-menu">John Doe</button>
  </div>
</header>
```

**Visual Specs:**
- Height: 64px
- Background: White
- Border-bottom: 1px solid `var(--border-color)`
- Shadow: `var(--shadow-sm)`
- Padding: 0 24px

---

## Page Specifications

### Dashboard (index.html)

#### Layout Structure
```
┌─────────────────────────────────────┐
│ Sidebar │ Top Nav Bar              │
│         ├────────────────────────────┤
│         │ KPI Cards (4 across)      │
│         ├────────────────────────────┤
│         │ Workflow Status Cards     │
│         ├────────────────────────────┤
│         │ Inventory Risk Table      │
└─────────────────────────────────────┘
```

#### KPI Cards
- Grid: 4 columns on desktop, 2 on tablet, 1 on mobile
- Height: 140px
- Icon: 48px, colored by status
- **Hero Number:** Source Serif 4 font, 36px, semibold
- **Label:** 14px, gray text
- **Trend Indicator:** Small arrow + percentage

#### Workflow Status Cards
- Display: Flex row, wrap on small screens
- Status indicator: Colored dot (green/yellow/red) + text
- Last run timestamp: Gray, small font
- **Running:** Green pulsing dot
- **Stopped:** Red solid dot
- **Error:** Yellow warning icon

### Inventory Management Page

#### Filters Section
- Sticky top bar below navigation
- Background: White, shadow on scroll
- Filters: Inline on desktop, accordion on mobile

#### Inventory Table
- Sortable columns (click header to sort)
- Fixed header on scroll
- Row actions: Edit/Adjust buttons right-aligned
- **Low Stock Rows:** Yellow background (#FFFBEB)
- **Out of Stock:** Red background (#FEE2E2)

### Order Management Tool

#### Search Bar
- Full width, prominent placement
- Search icon left-aligned
- Clear button appears when text entered
- Real-time validation feedback

#### Results Display
- **ShipStation Data:** Blue background (#EFF6FF)
- **Local DB Data:** Green background (#F0FDF4)
- Side-by-side comparison when both exist
- Actions column: Sync/Delete buttons

---

## Interaction Patterns

### Loading States

#### Skeleton Loaders
Used for initial page loads:
```html
<div class="skeleton-card">
  <div class="skeleton-header"></div>
  <div class="skeleton-line"></div>
  <div class="skeleton-line short"></div>
</div>
```
- Gray animated gradient shimmer
- Maintains layout to prevent jumps

#### Spinner
Used for button actions:
```html
<button class="btn-primary loading">
  <span class="spinner"></span>
  Loading...
</button>
```
- Disable button during load
- Replace text with spinner + "Loading..."

### Success/Error Feedback

#### Toast Notifications
```html
<div class="toast toast-success">
  <span class="toast-icon">✓</span>
  Order synced successfully
</div>
```
- Position: Top-right corner
- Auto-dismiss after 5 seconds
- Slide in from right
- **Success:** Green (#10B981)
- **Error:** Red (#EF4444)
- **Info:** Blue (#3B82F6)

### Confirmation Dialogs

Critical actions (delete, override) require confirmation:
```html
<div class="modal confirm-modal">
  <h3>Confirm Deletion</h3>
  <p>Are you sure you want to delete Order #100534?</p>
  <div class="modal-footer">
    <button class="btn-secondary">Cancel</button>
    <button class="btn-danger">Delete</button>
  </div>
</div>
```

### Auto-Refresh

- KPI cards refresh every 30 seconds
- Visual indicator: Small spinning icon during refresh
- No page reload, smooth data updates
- Disable during user interaction (typing, modal open)

---

## Responsive Design

### Breakpoints

```css
--breakpoint-sm: 640px   /* Mobile landscape */
--breakpoint-md: 768px   /* Tablet */
--breakpoint-lg: 1024px  /* Desktop */
--breakpoint-xl: 1280px  /* Large desktop */
```

### Mobile Adaptations

#### Navigation
- Sidebar collapses to hamburger menu
- Top bar shows menu icon left, logo center, user right
- Full-screen overlay menu

#### Tables
- Horizontal scroll with sticky first column
- OR card-based layout for narrow screens
- Row actions in dropdown menu

#### Forms
- Full width inputs
- Stack labels above inputs
- Larger touch targets (min 44px)

#### KPI Cards
- Single column on mobile
- Maintain visual hierarchy
- Preserve all information

---

## Accessibility

### WCAG 2.1 Level AA Compliance

#### Color Contrast
- **Text:** Minimum 4.5:1 against background
- **Large Text (18px+):** Minimum 3:1
- **UI Components:** Minimum 3:1 for borders/icons

#### Keyboard Navigation
- All interactive elements focusable via Tab
- Focus indicator: 2px blue outline + shadow
- Skip to main content link
- Modal trap focus (Esc to close)

#### Screen Reader Support
```html
<button aria-label="Delete order 100534">
  <span class="icon-trash" aria-hidden="true"></span>
</button>
```
- Semantic HTML (nav, main, aside, article)
- ARIA labels for icon-only buttons
- ARIA live regions for dynamic updates
- Alt text for all images

#### Form Accessibility
- Label associated with input (for/id)
- Required fields marked with aria-required
- Error messages linked with aria-describedby
- Clear validation feedback

---

## Edge Cases & Error States

### Empty States

#### No Data Available
```html
<div class="empty-state">
  <img src="empty-icon.svg" alt="">
  <h3>No orders found</h3>
  <p>There are no pending orders at this time.</p>
</div>
```

#### Search No Results
```html
<div class="empty-state">
  <img src="search-icon.svg" alt="">
  <h3>No results for "12345"</h3>
  <p>Try a different order number or check your spelling.</p>
  <button class="btn-secondary">Clear Search</button>
</div>
```

### Error States

#### API Error
- Display toast notification with error message
- Retry button when applicable
- Log error details for debugging

#### Offline State
```html
<div class="offline-banner">
  ⚠️ You're offline. Some features may not work.
</div>
```
- Sticky banner at top
- Yellow background
- Auto-hide when connection restored

#### Data Conflicts
- Highlight conflicting fields in red
- Show comparison side-by-side
- Provide resolution options

### Loading Timeouts

- Show skeleton for <3 seconds
- Replace with error message if >10 seconds
- Provide manual refresh option

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-11-03 | Initial UI specifications document | System |

---

## Maintenance Notes

This document should be updated whenever:
- New UI components are added
- Design system changes (colors, fonts, spacing)
- New interaction patterns are implemented
- Accessibility improvements are made
- Responsive breakpoints are modified

**Review Frequency:** Quarterly or after major feature releases
