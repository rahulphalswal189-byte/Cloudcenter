# ☁️ CloudVault — Cloud-Based Storage File System

A full-stack file storage web application built with **Django** (backend) and
**Bootstrap 5 + vanilla JS** (frontend), featuring a modern glassmorphism UI,
drag-and-drop uploads, folders, search, sharing, and a dark/light theme.

---

## 1. Tech Stack

| Layer      | Technology                                   |
|------------|-----------------------------------------------|
| Frontend   | HTML5, CSS3, JavaScript (ES6), Bootstrap 5    |
| Backend    | Python 3.10+, Django 5.0                      |
| Database   | SQLite (default Django DB, zero config)       |
| Auth       | Django's built-in auth system (hashed passwords, CSRF protection) |
| Payments   | Stripe (Checkout + subscriptions + webhooks)  |
| Animation  | AOS (scroll), Chart.js (storage chart), CSS transitions |

---

## What's New in This Upgrade (v2)

- 🔐 Forgot/Reset Password, Change Password, Remember Me, password strength meter
- 💳 Stripe **subscriptions** (not one-off payments): Monthly + Yearly billing,
  4 tiers (Free 5GB / Basic 100GB / Pro 1TB / Enterprise Unlimited), Billing
  History page, cancel/resume, invoice links, full renewal webhook handling
- 📦 Free tier raised from 1GB → **5GB**
- 🎨 Auto dark mode for logged-out visitors, AOS scroll animations, animated
  dashboard counters, a real storage-by-file-type chart (Chart.js), and
  toast notifications replacing static alert banners
- 🗂️ File manager: sort, type filter, favorites, grid/list toggle, breadcrumb
  navigation for nested folders

**Deferred from the original request** (each is a clean follow-up — ask
anytime): email verification on signup, dedicated Contact/About pages, file
move/copy, generated PDF invoices (Stripe's hosted invoice link is used
instead), rate limiting/caching, GSAP/Lottie animation libraries.

---

## 2. Project Structure

```
cloud_storage/
├── manage.py
├── requirements.txt
├── README.md
├── .gitignore
├── db.sqlite3                  # created after first migrate
├── media/                      # uploaded files land here
├── staticfiles/                # collectstatic output (production)
│
├── cloud_storage/              # PROJECT package
│   ├── __init__.py
│   ├── settings.py             # apps, DB, upload limits, security
│   ├── urls.py                 # root URL router
│   ├── wsgi.py
│   └── asgi.py
│
└── storage_app/                # APP package (all business logic)
    ├── __init__.py
    ├── apps.py
    ├── models.py                 # Folder, File, UserProfile, UserStorage, Plan, Subscription, Payment
    ├── forms.py                  # RegisterForm, FileUploadForm, etc.
    ├── views.py                  # all page + AJAX logic
    ├── urls.py                   # app URL routes (incl. Django auth password views)
    ├── admin.py                  # Admin Panel registrations
    ├── signals.py                # auto-create profile/storage, sync usage, seed plans
    ├── payments.py                # Stripe subscription Checkout + webhook logic
    ├── context_processors.py     # injects storage stats into every template
    ├── migrations/
    │   └── __init__.py
    ├── templatetags/
    │   ├── __init__.py
    │   └── storage_filters.py
    ├── templates/storage_app/
    │   ├── base.html             # sidebar + navbar layout
    │   ├── home.html
    │   ├── auth/                 # password reset/change flow (Django built-in views)
    │   │   ├── password_reset.html
    │   │   ├── password_reset_done.html
    │   │   ├── password_reset_confirm.html
    │   │   ├── password_reset_complete.html
    │   │   ├── password_reset_email.txt
    │   │   ├── password_reset_subject.txt
    │   │   ├── password_change.html
    │   │   └── password_change_done.html
    │   ├── login.html
    │   ├── register.html
    │   ├── dashboard.html
    │   ├── upload.html
    │   ├── my_files.html
    │   ├── profile.html
    │   ├── settings.html
    │   ├── shared_file.html
    │   ├── pricing.html
    │   ├── billing_history.html
    │   └── 404.html
    └── static/storage_app/
        ├── css/style.css
        └── js/script.js
```

---

## 3. Database Models

| Model         | Key Fields                                                                 |
|---------------|------------------------------------------------------------------------------|
| `User`        | Django's built-in user model (username, email, hashed password)             |
| `UserProfile` | avatar, bio, theme_preference — 1-to-1 with User                            |
| `UserStorage` | quota_bytes (-1 = unlimited), used_bytes, plan — 1-to-1 with User, auto-updated via signals |
| `Folder`      | name, owner, parent (self-referencing, supports nesting)                    |
| `File`        | file, file_name, file_size, file_type, uploaded_at, owner, folder, is_shared, share_token, is_favorite |
| `Plan`        | name, slug, storage_mb (0 = unlimited), price_monthly, price_yearly, stripe_price_id_monthly/yearly, is_active, order |
| `Subscription`| user, plan, interval, stripe_customer_id, stripe_subscription_id, status, current_period_end, cancel_at_period_end |
| `Payment`     | user, plan, interval, stripe_checkout_session_id, stripe_invoice_id, invoice_url, amount_usd, status |

---

## 4. Installation & Setup

### Step 1 — Create a virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 2 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 3 — Run database migrations
```bash
python manage.py makemigrations
python manage.py migrate
```
> The `migrations/` folder ships with only `__init__.py` — running
> `makemigrations` generates `0001_initial.py` tailored to your exact
> installed Django version, which is the safest approach.

### Step 4 — Create an admin (superuser) account
```bash
python manage.py createsuperuser
```

### Step 5 — Run the development server
```bash
python manage.py runserver
```

Visit:
- App → http://127.0.0.1:8000/
- Admin Panel → http://127.0.0.1:8000/admin/

---

## 5. Feature Checklist

✅ User Registration & Login (hashed passwords via Django auth)
✅ Logout
✅ Forgot Password / Reset Password (secure token-based, 1-hour expiry)
✅ Change Password (while logged in)
✅ Remember Me (session expiry control)
✅ Password Strength Meter (live, on register + reset forms)
✅ Dashboard with live stats, animated counters, and a storage-by-type chart
✅ Upload Files (multi-file, drag & drop, progress bar, validation)
✅ Download Files
✅ Delete Files (with confirmation modal)
✅ Rename Files
✅ Search Files (by name/type), plus Sort and Filter by type
✅ Grid / List view toggle
✅ Favorite Files
✅ Breadcrumb Navigation (nested folders)
✅ Folder Creation (nested folders supported)
✅ File Sharing via public link (optional feature, implemented)
✅ User Profile (avatar, bio)
✅ Storage Usage tracking (quota vs used vs remaining, unlimited-plan aware)
✅ Recent Uploads widget
✅ Admin Panel (Django admin, fully wired to all models)
✅ Responsive Design (Bootstrap 5 grid + custom breakpoints)
✅ CSRF Protection (Django middleware + `{% csrf_token %}` everywhere)
✅ File Type Validation (extension whitelist, server-side)
✅ Max Upload Size Validation (50MB/file, configurable in settings.py)
✅ Drag & Drop Upload
✅ Progress Bar while Uploading (real XHR progress events)
✅ Dark / Light Theme — manual toggle (persisted per-user) + automatic OS-based
   theme for logged-out visitors
✅ Scroll animations (AOS), animated counters, and toast notifications
✅ Payment Gateway (Stripe) — Monthly & Yearly subscriptions, 4 tiers including
   unlimited-storage Enterprise, upgrade/downgrade, Billing History, invoice
   links, cancel/resume, full webhook-driven renewal handling
✅ 5 GB free storage tier (up from 1 GB)

---

## 6. Security Notes

- Passwords are **never stored in plain text** — Django's `UserCreationForm`
  uses PBKDF2 hashing by default.
- Every POST form includes `{% csrf_token %}`; Django's `CsrfViewMiddleware`
  rejects any request without a valid token.
- File uploads are validated **server-side** (not just in the browser) against
  an extension whitelist and a max-size limit (`settings.ALLOWED_FILE_EXTENSIONS`,
  `settings.MAX_UPLOAD_SIZE`).
- All file/folder views use `@login_required` and filter querysets by
  `owner=request.user`, so users can never access each other's files directly.
- Shared files use a random 32-byte URL-safe token (`secrets.token_urlsafe`),
  not sequential/guessable IDs.
- Before deploying to production: set `DEBUG = False`, generate a fresh
  `SECRET_KEY`, set `ALLOWED_HOSTS`, and enable `CSRF_COOKIE_SECURE` /
  `SESSION_COOKIE_SECURE` (both are stubbed in `settings.py`).

---

## 7. Payment Gateway (Stripe) Setup

CloudVault uses **Stripe Checkout in subscription mode** for Monthly/Yearly
storage plans (Free / Basic / Pro / Enterprise). Card details are entered on
Stripe's own hosted page — they never touch our server, so we stay out of
PCI-DSS scope entirely.

### 7.1 Get free test-mode API keys
1. Create a free account at https://dashboard.stripe.com/register
2. Go to https://dashboard.stripe.com/test/apikeys
3. Copy your **Publishable key** (`pk_test_...`) and **Secret key** (`sk_test_...`)

### 7.2 Set them as environment variables
```bash
# macOS / Linux
export STRIPE_PUBLIC_KEY="pk_test_xxxxxxxx"
export STRIPE_SECRET_KEY="sk_test_xxxxxxxx"

# Windows (PowerShell)
$env:STRIPE_PUBLIC_KEY="pk_test_xxxxxxxx"
$env:STRIPE_SECRET_KEY="sk_test_xxxxxxxx"
```
(Never commit real keys to source control — `settings.py` already reads
these from the environment, falling back to harmless placeholders.)

### 7.3 Test webhooks locally (required for renewals/cancellations)
Stripe calls your `/payments/webhook/` endpoint directly for everything
that happens *after* the initial checkout — renewal charges, failed
payments, and cancellations — since those don't involve the customer's
browser. To test this locally, install the
[Stripe CLI](https://stripe.com/docs/stripe-cli) and run:
```bash
stripe listen --forward-to localhost:8000/payments/webhook/ \
  --events checkout.session.completed,invoice.paid,invoice.payment_failed,customer.subscription.updated,customer.subscription.deleted
```
This prints a `whsec_...` signing secret — set it too:
```bash
export STRIPE_WEBHOOK_SECRET="whsec_xxxxxxxx"
```

### 7.4 Try a test subscription
1. Run the server and visit `/pricing/`
2. Toggle **Monthly**/**Yearly**, then click **Upgrade** on Basic, Pro, or
   Enterprise
3. On Stripe's Checkout page, use test card `4242 4242 4242 4242`, any
   future expiry date, any CVC, and any ZIP
4. You'll be redirected back and your storage quota upgrades instantly;
   check `/billing/` to see the payment logged and manage the subscription

### 7.5 How it works under the hood
- `storage_app/payments.py` — creates subscription Checkout Sessions and
  handles every lifecycle event: initial activation, renewal charges
  (`invoice.paid`, logged to Billing History), failed renewals (marks
  `past_due`), plan/status changes, and cancellations (auto-downgrades to
  Free once the subscription actually ends)
- `models.Plan` — editable pricing tiers in the Admin Panel (monthly +
  yearly price each); supports plugging in real Stripe recurring Price IDs
  once you've created Products in your Stripe Dashboard, or falls back to
  building the price inline. `storage_mb = 0` means unlimited (Enterprise)
- `models.Subscription` — tracks the ongoing billing state (status,
  current period end, scheduled cancellation) per user
- `models.Payment` — a full audit trail of every charge — initial and
  renewal — with a link to Stripe's own hosted invoice for each one,
  visible in the Admin Panel and on the Billing History page
- Four starter plans (Free/Basic/Pro/Enterprise) are seeded automatically
  the first time you run `migrate`

---

## 8. Testing Steps (manual QA checklist)

1. **Register** a new account → confirm you land on the Dashboard and a
   `UserProfile`/`UserStorage` row was auto-created (check `/admin/`).
2. **Logout**, then **Login** again with the same credentials.
3. Try logging in with a wrong password → confirm a friendly error shows.
4. Go to **Upload**, drag a `.jpg` and a `.pdf` onto the drop zone → confirm
   the progress bar animates and both appear in **My Files**.
5. Try uploading a disallowed extension (e.g. `.exe`) → confirm it's rejected
   with a clear message.
6. Try uploading a file larger than 50MB → confirm it's rejected.
7. **Rename** a file, **delete** a file (with the confirmation modal), and
   confirm the Dashboard's "Total Files" / "Storage Used" numbers update.
8. **Create a folder**, upload a file into it, and confirm it only shows
   inside that folder.
9. Use the **Search bar** to find a file by partial name.
10. Click **Share** on a file, copy the link, open it in an incognito window
    (logged out) → confirm the file downloads without needing to log in.
11. Toggle **Dark/Light theme** from the navbar and from Settings → refresh
    the page → confirm the preference persisted.
12. Resize the browser to mobile width → confirm the sidebar collapses into
    a toggle-able hamburger menu.
13. Visit a nonexistent URL, e.g. `/does-not-exist/` → confirm the custom
    404 page renders.
14. Log in as a superuser at `/admin/` → confirm Files, Folders, Profiles,
    and Storage records are all visible and editable.
15. Visit `/pricing/`, toggle **Yearly**, upgrade to **Pro** using Stripe
    test card `4242 4242 4242 4242` → confirm you're redirected back, your
    Dashboard's "Remaining Storage" jumps up, and a `Payment` row with
    status `completed` appears in the Admin Panel and on `/billing/`.
16. Click **Upgrade** then **cancel** on Stripe's page (back button) →
    confirm you land on a friendly "Checkout was cancelled" message with
    no `Payment` marked completed.
17. On `/billing/`, click **Cancel Subscription** → confirm the page shows
    "will end at the close of the current billing period" and a
    **Resume Subscription** button appears.
18. From the Login page, click **Forgot password?**, submit your email →
    check your terminal (console email backend) for the reset link, open
    it, set a new password (watch the strength meter react as you type),
    and confirm you can log in with it.
19. While logged in, go to **Settings → Change Password** → confirm the
    old password is required and the new one takes effect immediately.
20. On **My Files**, star a file (favorite), then filter by **Favorites**,
    **sort** by size/name, and **filter by file type** → confirm each
    control narrows the results correctly. Toggle **Grid/List view**.
21. Upload files into a nested folder (folder inside a folder) → confirm
    the **breadcrumb trail** shows the full path and each crumb navigates
    correctly.

---

## 9. Screenshots (what each page looks like)

> Run the server and visit each route to see it live — described here
> since this is a text deliverable.

- **Home** — Full-width gradient hero with a "Create Free Account" call to
  action and three glass feature cards below it.
- **Login / Register** — Centered glass card floating over the gradient
  background, with icon-labeled inputs and a gradient submit button.
- **Dashboard** — Four gradient-icon stat cards (Files, Used, Remaining,
  Folders) in a row, a quick-upload glass panel, and a recent uploads table.
- **Upload** — Large dashed drop-zone with a cloud icon; selected files list
  below it; an animated striped progress bar appears during upload.
- **My Files** — Folder tiles at the top, file cards in a responsive grid
  below, each with download/rename/share/delete icon buttons.
- **Profile** — Circular avatar (or gradient placeholder), bio editor, and a
  storage usage bar.
- **Settings** — Light/Dark radio toggle cards.
- **Admin Dashboard** — Standard Django admin, styled by Django itself,
  listing Files/Folders/Profiles/Storage with search & filters.
- **404 Page** — Centered glass card with a cloud-slash icon and a
  "Back to Home" button.

---

## 10. Future Enhancements

**Deferred from the latest redesign request (highest priority next steps):**
- Email verification on signup (needs your SMTP credentials — see §7's
  email backend config, same mechanism as password reset)
- Contact and About pages
- File Move / Copy (Rename and folder-based organization are done; drag-file-
  between-folders is not)
- Generated PDF invoices (currently linked to Stripe's own hosted invoice
  instead, which is the standard practical approach)
- Rate limiting and response caching
- GSAP / Lottie animation libraries (AOS + Chart.js + CSS are in place now)

**Longer-term roadmap:**
- Real-time collaborative folders (WebSockets / Django Channels)
- Chunked/resumable uploads for very large files
- Trash bin with 30-day auto-purge instead of hard delete
- Per-folder sharing (not just per-file)
- Two-factor authentication
- Cloud object storage backend (S3 / GCS) instead of local disk for scale
- Full-text search inside document contents (not just filename)
- File versioning / revision history
- Team workspaces with role-based permissions

---

## 11. License

This project was generated as a learning/reference implementation. Feel
free to use, modify, and extend it for personal or commercial projects.
