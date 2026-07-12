# HealthCore Website

Public Next.js website for HealthCore.

## Purpose

- Replace static public pages with a reusable component-based application.
- Keep landing and application form behavior available in the new architecture.
- Separate public experience from internal backoffice features.

## Stack

- Next.js 16 (App Router)
- React 19
- TypeScript
- Tailwind CSS 4

## Structure

- `app/` routes and layouts
- `components/` reusable UI sections and form elements
- `lib/` public content constants
- `public/` static assets
- `styles/` reserved for future style modules

## Routes

- `/` public landing page
- `/application` patient intake form with client-side validation

## Run

```bash
cd uis/website
npm install
npm run dev
```
