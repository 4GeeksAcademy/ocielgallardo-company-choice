# Design System: HealthCore

**Project:** Internal digital transformation unit - 4Geeks Academy
**Version:** 1.0 (Based on Milestone 1 & 2)
**Status:** Master Documentation

## 1. Brand Identity

HealthCore is not just software; it is the bridge between operational efficiency and human care.

- **Personality:** Reliable, clinical, human, modern, and secure.
- **Tone of Voice:** Clear, empathetic, and professional. We avoid excessive medical jargon to prioritize patient understanding and staff agility.
- **Logo Concept:** Circular icon that integrates a stylized medical cross with a globe, symbolizing its international network (USA/UK).
- **Tagline:** "Smart, secure, and human healthcare."

---

## 2. Color System

The system uses a professional clinical blue foundation extended with semantic colors for predictive risk analysis.

### Primary Colors

| Token | HEX | Primary Use |
| :--- | :--- | :--- |
| `primary-600` | `#2563eb` | Primary buttons, active icons, branding. |
| `primary-700` | `#1d4ed8` | Hover states, strong accents. |
| `primary-900` | `#1e3a8a` | Headers, hero text, dark brand backgrounds. |

### Neutral Colors (Slate Scale)

| Token | HEX | Primary Use |
| :--- | :--- | :--- |
| `slate-50` | `#f8fafc` | Page backgrounds, clean work areas. |
| `slate-200` | `#e2e8f0` | Card borders, dividers, disabled inputs. |
| `slate-600` | `#475569` | Secondary text, form labels. |
| `slate-800` | `#1e293b` | Main body text, secondary headings. |
| `slate-950` | `#020617` | High-contrast headings, dark mode. |

### Semantic Colors and Risk Levels

| Status / Risk | HEX / Tailwind | Use |
| :--- | :--- | :--- |
| `Success` | `green-500` | Confirmations, attended appointments, paid invoices. |
| `Warning` | `amber-500` | Low-medium risk, pending reminders. |
| `Danger / Critical`| `red-600` | Critical alerts, no-shows, rejected invoices. |
| `Info` | `cyan-500` | System information, help, tips. |

**Accessibility:** Minimum WCAG AA contrast (4.5:1) guaranteed for all readable text on backgrounds.

---

## 3. Typography

We prioritize readability in high data-density contexts (Dashboards).

- **Font:** `Inter` (Sans-serif).
- **Text Scale:**
    - `h1`: 3xl to 5xl (Extrabold) - Hero and landing titles.
    - `h2`: 2xl to 3xl (Bold) - Section titles and large KPIs.
    - `h3`: xl (Semibold) - Card and widget titles.
    - `body`: base (Regular) - Main text.
    - `caption`: sm/xs (Medium) - Metadata, table labels, legal notes.
- **Line-height:** 1.5 for body text to reduce visual fatigue.

---

## 4. Spacing & Layout

- **Containers:**
    - `max-w-7xl`: For public landing and dashboards.
    - `max-w-5xl`: For registration forms (improves focus).
- **Grid System:** 1 column on mobile -> 2 columns on tablet -> 3-5 columns on desktop (dashboard).
- **Padding:** Standard sections `py-14`, side containers `px-4 sm:px-6 lg:px-8`.
- **Border Radius:**
    - `lg (8px)`: Small elements (buttons).
    - `xl (12px)`: Standard cards.
    - `2xl (16px)`: Landing sections and large containers.
    - `full`: Badges, avatars, and pills.

---

## 5. Components Library

### Navigation and Structure
- **Header:** Sticky, glass background (blur), nav links and "Registration" CTA (`blue-600`).
- **Footer:** 4 columns (Brand, Services, Legal, Locations), `slate-950` background for contrast.

### Cards and Visualization
- **Service Cards:** White background, `rounded-2xl`, soft shadow, hover elevation (`-translate-y-1`).
- **KPI Widgets:** Large numeric value (`text-3xl`), label below, trend/risk indicator on the right.
- **Probability Bars:**
    ```text
    [||||||||-- 82% --] (Color: Red-600 if > 70%)
    ```

### Forms
- **Inputs:** `border-slate-200`, `focus:ring-2`, `focus:ring-blue-600`.
- **Validation:** Error messages in `red-600` with `aria-live="polite"`.

---

## 6. Page Templates

### A) Public Landing (Current)
1. **Hero:** `blue-900` to `blue-700` gradient with a glass card for the central message.
2. **Services:** 3x2 grid with specialty icons.
3. **Statistics:** Impact section (12 clinics, 200+ professionals).
4. **Patient Flow:** 4-step visual diagram (Booking -> Validation -> Care -> Follow-up).

### B) Registration Form (Current)
- Linear structure by fieldsets: Personal Data -> Location -> Clinic/Reason -> Legal Consent.

### C) Operational Dashboard (Future)
- **Priya Nair View (Patient Experience):**
    - Top: Current No-Show Rate KPI (vs 22% baseline).
    - Center: List of "Upcoming appointments with high No-Show risk".
    - Actions: Quick "Send WhatsApp/SMS Reminder" button.
- **Tom Callahan View (Revenue Cycle):**
    - Center: "Invoices with rejection probability > 60%".
    - Alerts: CriticalAlerts for AI-detected coding errors.

---

## 7. Iconography and Images

- **Icon Style:** Linear, 2px stroke (Lucide/Heroicons style).
- **Images:** Real, diverse, and optimistic medical photography. We avoid overused generic stock images.
- **Rule:** Never use images of needles, blood, or suffering patients in operational interfaces.

---

## 8. Accessibility and Compliance

- **Focus:** Always visible focus rings (`ring-offset-2`).
- **Navigation:** "Skip to content" links present.
- **Privacy:** Internal dashboards must anonymize PHI (Protected Health Information) unless the role has specific permissions. Explicit HIPAA/GDPR consent in each form footer.

---

## 9. Brand Do's & Don'ts

| Do's | Don'ts |
| :--- | :--- |
| Use blues to convey calm and security. | Do not use harsh shadows or neon colors. |
| Maintain a professional and empathetic tone. | Do not use technical jargon that confuses patients. |
| Prioritize the main action (CTA). | Do not overload the UI with too many secondary KPIs. |
| Ensure WCAG AA contrast. | Do not use red for states that are not critical. |

---

## 10. Domain Mapping

| Entity | Suggested UI Component |
| :--- | :--- |
| `Appointment` | Card in a list or table row with probability. |
| `Invoice` | Table row with status badge (Rejected/Paid). |
| `NoShowPrediction`| Visual risk indicator (Low/Medium/High). |
| `CriticalAlert` | Top banner or card with `red-600` border. |

---
**Generated by Stitch for the HealthCore team.**
"Smart, secure, and human healthcare."
