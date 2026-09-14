# Rule: Form Validation

## Purpose
Standardize client-side form validation UX across `uis/backoffice` (and `uis/website` intake where applicable) without changing backend contracts.

## Canonical Pattern
- Reference implementation: `uis/backoffice/components/forms/RegisterForm.tsx` (`validate()` per field + `getFieldErrors()` API mapping + 409 handling + `useFormSubmit`).
- Structure every form as: `validate(values)` → `setFieldErrors` → abort on errors → `runSubmit()` → map API `details` via `getFieldErrors()` → global `FormMessage` only for non-field failures.

## Requirements
- Use `noValidate` on `<form>`; never rely on native browser bubbles.
- Show inline errors via `Input`/`Select` `error=` prop (`aria-invalid`, `aria-describedby`, `role="alert"`). Keep one global `FormMessage variant="error"` for form-level/API failures only.
- Trim string inputs before validation and before submit (`email.trim()`, `name.trim()`).
- Disable submit while `isSubmitting`; restore label state (`Saving…`, `Creando cuenta…`).
- Map API field errors explicitly per form (email, password, name, phone, address); on 409 set the conflicting field (e.g. email already registered), not just the global message.
- Type form status as `{ kind: "success" | "error", message: string }`; never sniff message substrings (e.g. `includes("No se")`).

## Field Rules
- Email: required, `/^[^\s@]+@[^\s@]+\.[^\s@]+$/`; normalize with `trim()`.
- Password: required, min 8 chars; confirm field must match (`Las contraseñas no coinciden.`).
- Login (`LoginForm.tsx`): upgrade to per-field errors (email + password) instead of a single global message.
- Numeric (rates, quantities, `unit_cost`): required, `Number(value) > 0`; surface API 400 inline on the offending field (see outbound stock guard).
- Optional contact email: validate format only when non-empty.
- Dates (contract renewal): ISO date input; `TODO:` confirm past-date policy with business owner.
- Categories/checkbox groups: error block with `role="alert"` under the group, same red-600 styling as inputs.

## Language and Tone
- Keep existing labels as-is (mixed EN/ES inventory legacy). New messages: labels follow the form locale; validation hints stay actionable (`El email es obligatorio.`, `Introduce una tarifa mayor que 0.`).
- `TODO:` Confirm canonical locale policy (EN labels + ES hints vs full ES) before bulk-renaming forms.

## Accessibility and Compliance
- Associate every input with `<label htmlFor>`; announce errors via `role="alert"` / `aria-live="polite"`.
- Never echo passwords, tokens, or PHI in error text. Auth errors stay generic on the global message (401 → `Credenciales incorrectas.`) with `login_failed` telemetry; field errors carry format hints only.
- Record `inventory_form_abandoned` / `inbound_order_rejected` telemetry where already instrumented; do not add new event types from this rule alone.

## Quality Check
- Run `cd uis/backoffice && npm run lint` and `npx tsc --noEmit` after form changes.
- If checks cannot run, report the gap in delivery notes per `typescript-guidelines.md`.
