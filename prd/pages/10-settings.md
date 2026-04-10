# Account Settings

> **Route:** `/dashboard/settings`
> **Module:** Settings
> **Generated:** 2026-04-10

## Overview

The Account Settings page allows both students and teachers to manage three categories of preferences: **Profile Information** (name, department, degree, semester), **Password** (change current password), and **Theme & Notifications** (theme mode, notifications toggle, weekly digest, focus mode). All changes are persisted immediately via POST form submissions and the user is redirected back to the settings page with a success or error message in the query string.

## Layout

The page uses a `settings-shell` grid layout with three main sections rendered as styled cards:

```
┌────────────────────────────────────────────────────────┐
│  [Logo] StudentLID                                     │
│                                                        │
│  Account Settings                        [User Avatar] │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │  [Profile Card]                                  │  │
│  │  👤 Display Name: [___________]                  │  │
│  │  📚 Department:  [___________] (students only)  │  │
│  │  🎓 Degree:      [___________] (students only)  │  │
│  │  📅 Semester:    [___________] (students only)  │  │
│  │                    [Save Profile]                │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │  [Password Card]                                 │  │
│  │  Current Password:    [___________]              │  │
│  │  New Password:        [___________]              │  │
│  │  Confirm Password:    [___________]              │  │
│  │                       [Update Password]           │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │  [Preferences Card]                              │  │
│  │  Theme:  ○ Light  ○ Calm  ○ Contrast            │  │
│  │  □ Enable Notifications                          │  │
│  │  □ Weekly Digest                                │  │
│  │  □ Focus Mode                                   │  │
│  │                    [Save Preferences]            │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

## Fields

### Profile Form

| Field | Type | Required | Default | Validation | Role-Specific |
|-------|------|----------|---------|------------|---------------|
| Display Name | Text input | Yes | — | Cannot be empty after trim | All roles |
| Department | Text input | No | `None` | — | Students only |
| Degree | Text input | No | `None` | — | Students only |
| Semester | Text input | No | `None` | — | Students only |

**Note:** Department, Degree, and Semester fields are only shown to students. Teachers only see the Display Name field in the profile section.

### Password Form

| Field | Type | Required | Default | Validation | Notes |
|-------|------|----------|---------|------------|-------|
| Current Password | Password input | Yes | — | Must match stored hash | — |
| New Password | Password input | Yes | — | Minimum 6 characters | — |
| Confirm Password | Password input | Yes | — | Must match New Password | — |

### Preferences Form

| Field | Type | Default | Validation | Notes |
|-------|------|---------|------------|-------|
| Theme Mode | Radio group | `light` | Must be one of: `light`, `calm`, `contrast` | Stored in User document |
| Notifications Enabled | Checkbox | `True` | — | Toggles boolean |
| Weekly Digest | Checkbox | `True` | — | Toggles boolean |
| Focus Mode | Checkbox | `False` | — | Toggles boolean |

## Interactions

### Page Load
- Authenticates user via JWT cookie; redirects to `/auth/login` if unauthenticated
- Loads `email_profile` from `ScoringService.get_student_email_profile()` (auto-parsed from email) for informational display
- Displays feedback messages from query string (`settings_feedback`):
  - `?profile_success=Profile+updated+successfully`
  - `?profile_error=Display+name+cannot+be+empty`
  - `?password_success=Password+updated+successfully`
  - `?password_error=Current+password+is+incorrect`
  - `?password_error=New+password+must+be+at+least+6+characters`
  - `?password_error=New+password+and+confirm+password+must+match`
  - `?prefs_success=Preferences+saved`
  - `?prefs_error=Invalid+theme+mode`

### Update Profile
- **Trigger:** Click "Save Profile"
- **API:** POST to `/dashboard/update_profile`
- **Validation:** Name cannot be empty; `department`, `degree`, `semester` are optional
- **Behavior:** Updates `User.name`, and for students, `User.department`, `User.degree`, `User.semester`
- **Success redirect:** `?profile_success=Profile+updated+successfully`
- **Error redirect:** `?profile_error=Display+name+cannot+be+empty`

### Update Password
- **Trigger:** Click "Update Password"
- **API:** POST to `/dashboard/update_password`
- **Validation:**
  - Current password must match stored hash
  - New password minimum 6 characters
  - New password and confirm password must match
- **Success redirect:** `?password_success=Password+updated+successfully`
- **Error redirects:** `?password_error=Current+password+is+incorrect`, `?password_error=New+password+must+be+at+least+6+characters`, `?password_error=New+password+and+confirm+password+must+match`

### Update Preferences
- **Trigger:** Click "Save Preferences"
- **API:** POST to `/dashboard/update_preferences`
- **Validation:** `theme_mode` must be one of `light`, `calm`, `contrast`
- **Behavior:** Updates `User.theme_mode`, `User.notifications_enabled`, `User.weekly_digest`, `User.focus_mode`
- **Success redirect:** `?prefs_success=Preferences+saved`
- **Error redirect:** `?prefs_error=Invalid+theme+mode`

## API Dependencies

| API | Method | Path | Trigger | Notes |
|-----|--------|------|---------|-------|
| Settings Page | GET | `/dashboard/settings` | Navigation | Renders settings with feedback from query params |
| Update Profile | POST | `/dashboard/update_profile` | Profile form | Updates name; department/degree/semester for students |
| Update Password | POST | `/dashboard/update_password` | Password form | Hashes new password with pbkdf2_sha256 |
| Update Preferences | POST | `/dashboard/update_preferences` | Preferences form | Updates theme and notification booleans |

## Page Relationships

- **From:** Dashboard sidebar ("Account Settings" link)
- **To:** `/dashboard` (back), `/auth/logout`
