# Reset Password

> **Route:** `/auth/reset-password`
> **Module:** Authentication
> **Generated:** 2026-04-10

## Overview

The Reset Password page is the destination of the one-time reset link sent to a user's email. It allows the user to set a new password for their account, provided the token embedded in the URL is valid and has not expired. The page validates the token server-side on load, then accepts a new password and confirmation. The link is single-use — after a successful reset, the token is invalidated.

## Layout

The page uses the same centered single-card layout as the Forgot Password page.

```
┌─────────────────────────────────────┐
│  [Logo] StudentLID                  │
│                                     │
│  Reset password                    │
│  Set a new password for your       │
│  account.                          │
│                                     │
│  [Error alert if applicable]        │
│                                     │
│  New password (min 8 chars)         │
│  [___________________________]       │
│                                     │
│  Confirm new password               │
│  [___________________________]       │
│                                     │
│  [     Update password →     ]     │
│                                     │
│  Back to login                      │
└─────────────────────────────────────┘
```

If the token is invalid or expired, an error is shown and the form inputs are hidden or disabled.

## Fields

### Form Fields

| Field | Type | Required | Default | Validation | Business Description |
|-------|------|----------|---------|------------|---------------------|
| Token | Hidden field | Yes | — | Must be a valid, non-expired token | Identifies the password reset session |
| New Password | Password input | Yes | — | Minimum 8 characters | New account password |
| Confirm Password | Password input | Yes | — | Must match New Password | Confirmation must match to prevent typos |

## Interactions

### Page Load (via Reset Link)
- **URL contains:** `?token=RAW_TOKEN`
- **Server behavior:**
  1. Extracts `token` from query parameter
  2. Calls `AuthService.validate_reset_token(token)`:
     - Hashes the raw token and looks up the hash in MongoDB
     - Checks that `expires_at` is set and the current time is before expiry
     - Returns the associated `User` or `None`
  3. If token is missing, invalid, or expired: renders the page with an error message
  4. If token is valid: renders the form with the token as a hidden field

### Page Load (Direct/Navigated)
- If accessed without a token (`/auth/reset-password` with no query string), the page immediately shows error: *"Invalid or missing reset token. Please request a new link."*

### Submit New Password
- **Trigger:** User enters a new password and confirmation, then clicks "Update password"
- **API:** POST to `/auth/reset-password` as `application/x-www-form-urlencoded`
- **Validation:**
  - `password` and `confirm_password` must match → error: *"Passwords do not match."*
  - `password` must be at least 8 characters → error: *"Password must be at least 8 characters long."*
- **Server behavior:**
  1. Re-validates the token (has not changed since page load)
  2. If valid: calls `AuthService.reset_password_with_token(token, new_password)`
     - Sets `User.password` to the new PBKDF2 hash
     - Clears `User.password_reset_token_hash = None`
     - Clears `User.password_reset_expires_at = None`
     - Sets `auth_provider = "local"` if previously unset
  3. Redirects to `/auth/login?message=Password+updated.+Please+sign+in.`
- **Token already used/expired:** Renders error: *"This reset link is invalid or has expired. Please request a new one."*

### Back to Login
- **Trigger:** User clicks "login" text link
- **Behavior:** Navigates to `/auth/login`

## Security Design

### Token Invalidation
The token is single-use: `reset_password_with_token()` sets both `password_reset_token_hash` and `password_reset_expires_at` to `None` immediately upon successful password update, making the URL useless if revisited.

### Token Expiry
Tokens expire 60 minutes after generation. After expiry, the link shows an error and the user must request a new one.

### Google Account Handling
The forgot-password submission silently succeeds for Google OAuth accounts (which have no local password). The email cannot actually be reset for Google accounts via this flow.

## Dev-Only Email Preview

A **dev-only endpoint** exists for testing the email template without sending real emails:

- **Route:** `/auth/dev/email-preview/reset-password?name=Student&token=preview-token-123`
- **Access:** Only works when `ENVIRONMENT` is one of `development`, `dev`, `local`, `test`
- **Behavior:** Returns the fully rendered branded HTML email body as an `HTMLResponse`; no email is sent
- **Use case:** QA of email styling and content during development

## API Dependencies

| API | Method | Path | Trigger | Notes |
|-----|--------|------|---------|-------|
| Reset Password Page | GET | `/auth/reset-password?token=XXX` | Via email link | Validates token, renders form or error |
| Reset Password Submit | POST | `/auth/reset-password` | Form submission | Resets password, clears token |
| Dev Email Preview | GET | `/auth/dev/email-preview/reset-password` | Dev testing | Environment-gated; renders HTML email |

## Page Relationships

- **From:** `/auth/forgot-password` (via email link), `/auth/login` (via email link)
- **To:** `/auth/login` (after successful reset)
