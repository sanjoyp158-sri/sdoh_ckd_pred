# 🎨 Frontend Visual Guide

## Screen Layouts

### 1. Login Page

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│         [Purple Gradient Background]                    │
│                                                         │
│     ┌───────────────────────────────────────┐          │
│     │                                       │          │
│     │   CKD Early Detection System          │          │
│     │   Provider Dashboard                  │          │
│     │                                       │          │
│     │   Username: [________________]        │          │
│     │                                       │          │
│     │   Password: [________________]        │          │
│     │                                       │          │
│     │        [    Sign In    ]              │          │
│     │                                       │          │
│     └───────────────────────────────────────┘          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Colors:**
- Background: Purple gradient (elegant, professional)
- Card: White with shadow
- Button: Blue (#2563eb)
- Text: Dark gray

---

### 2. Patient List Dashboard

```
┌─────────────────────────────────────────────────────────────────────────┐
│ CKD Early Detection System                    [User] [Logout]           │
├─────────────────────────────────────────────────────────────────────────┤
│ [👥]  │                                                                  │
│ Patients│  Patient Risk Dashboard              [150 patients]           │
│         │                                                                │
│         │  ┌──────────┬──────────┬──────────┬──────────┬──────────┐    │
│         │  │Risk Tier │CKD Stage │Date From │Date To   │Search    │    │
│         │  │[All ▼]   │[All ▼]   │[____]    │[____]    │[______]  │    │
│         │  └──────────┴──────────┴──────────┴──────────┴──────────┘    │
│         │                                                                │
│         │  ┌────────────────────────────────────────────────────────┐   │
│         │  │ ID ↕ │Age│Sex│Risk↕│Tier    │Stage│eGFR↕│Date↕│Status│   │
│         │  ├────────────────────────────────────────────────────────┤   │
│         │  │P001│65 │M  │0.82 │🔴 HIGH │3a   │45.2 │Jan 15│⏳    │   │
│         │  │P002│58 │F  │0.71 │🔴 HIGH │3b   │38.5 │Jan 14│✓     │   │
│         │  │P003│72 │M  │0.55 │🟡 MOD  │2    │62.1 │Jan 13│⏳    │   │
│         │  │P004│45 │F  │0.28 │🟢 LOW  │2    │75.8 │Jan 12│✓     │   │
│         │  │...                                                     │   │
│         │  └────────────────────────────────────────────────────────┘   │
│         │                                                                │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Sidebar navigation (blue highlight on active)
- Filter bar with dropdowns and date pickers
- Sortable table (click headers)
- Color-coded risk badges
- Hover effect on rows (light gray background)
- Click row to view details

---

### 3. Patient Detail View

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [← Back to Patients]  Patient P00123                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ ┌──────────────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│ │  Risk Assessment     │  │Demographics  │  │ Clinical Indicators │   │
│ │                      │  │              │  │                     │   │
│ │    ╭─────────╮       │  │ Age: 65 yrs  │  │ eGFR: 45.2         │   │
│ │   ╱   82%    ╲       │  │ Sex: Male    │  │ Stage: 3a          │   │
│ │  │  Risk Score│      │  │              │  │ UACR: 450.5        │   │
│ │   ╲           ╱       │  └──────────────┘  │ HbA1c: 7.2%        │   │
│ │    ╰─────────╯       │                     │ BP: 145/92         │   │
│ │                      │  ┌──────────────┐  │ BMI: 28.5          │   │
│ │   [🔴 HIGH RISK]     │  │Admin Metrics │  │                     │   │
│ │                      │  │              │  │ Comorbidities:      │   │
│ │ Baseline: 35%        │  │ Visits: 8    │  │ [Diabetes] [HTN]   │   │
│ │ Predicted: Jan 15    │  │ Insurance:   │  │                     │   │
│ │                      │  │  Medicare    │  └─────────────────────┘   │
│ │ [Acknowledge Review] │  │ Last: Dec 10 │                            │
│ └──────────────────────┘  └──────────────┘  ┌─────────────────────┐   │
│                                              │ SDOH Indicators     │   │
│ ┌────────────────────────────────────────┐  │                     │   │
│ │ Top Risk Factors (SHAP Analysis)       │  │ ADI: 85th %ile     │   │
│ │                                        │  │ Food Desert: Yes    │   │
│ │ High eGFR Decline    ████████████ 0.15│  │ Housing: 45%        │   │
│ │ High ADI Percentile  ██████████ 0.12  │  │ Transport: 60%      │   │
│ │ Food Desert Status   ████████ 0.09    │  │ Location: Rural     │   │
│ │ Low Visit Frequency  ██████ 0.07      │  │                     │   │
│ │ High UACR           █████ 0.06        │  └─────────────────────┘   │
│ │                                        │                            │
│ │ Legend: 🔵 Clinical 🟣 Admin 🌸 SDOH  │                            │
│ └────────────────────────────────────────┘                            │
│                                                                          │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ eGFR Trend                                                         │ │
│ │                                                                    │ │
│ │  90 ┤                                                              │ │
│ │  80 ┤  ●                                                           │ │
│ │  70 ┤     ●                                                        │ │
│ │  60 ┤        ●                                                     │ │
│ │  50 ┤           ●                                                  │ │
│ │  40 ┤              ●────●                                          │ │
│ │  30 ┤                                                              │ │
│ │     └────────────────────────────────────────────────────────────│ │
│ │      Jan  Mar  May  Jul  Sep  Nov  Jan                           │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Risk score with circular gauge (color-coded border)
- Large risk tier badge (red/yellow/green)
- SHAP horizontal bar chart (interactive)
- Organized info cards with clear labels
- eGFR trend line chart
- Acknowledge button (turns green when clicked)
- Comorbidity tags
- Clean, medical-professional design

---

## Color Scheme

### Risk Tiers
- 🔴 **High Risk**: `#ef4444` (red)
- 🟡 **Moderate Risk**: `#f59e0b` (amber)
- 🟢 **Low Risk**: `#10b981` (green)

### UI Elements
- **Primary**: `#2563eb` (blue) - buttons, links
- **Background**: `#f9fafb` (light gray)
- **Cards**: `#ffffff` (white)
- **Text**: `#111827` (dark gray)
- **Borders**: `#e5e7eb` (light gray)

### SHAP Categories
- 🔵 **Clinical**: `#3b82f6` (blue)
- 🟣 **Administrative**: `#8b5cf6` (purple)
- 🌸 **SDOH**: `#ec4899` (pink)

---

## Responsive Design

The dashboard adapts to different screen sizes:

- **Desktop** (>1200px): Full layout with sidebar
- **Tablet** (768-1200px): Stacked cards, collapsible sidebar
- **Mobile** (<768px): Single column, hamburger menu

---

## Interactions

### Hover Effects
- Table rows: Light gray background
- Buttons: Darker shade
- Cards: Subtle shadow increase

### Click Actions
- Table row → Navigate to patient detail
- Column header → Sort by that column
- Acknowledge button → Mark as reviewed (green checkmark)
- Back button → Return to patient list

### Loading States
- Skeleton screens while data loads
- Spinner for async operations
- "Loading patients..." message

---

## Accessibility

✅ Keyboard navigation
✅ ARIA labels
✅ Color contrast (WCAG AA)
✅ Focus indicators
✅ Screen reader support

---

## To See It Live

Run these commands in your terminal:

```bash
cd frontend
npm run dev
```

Then open: **http://localhost:3000**

The interface is fully functional and ready to connect to the backend API!
