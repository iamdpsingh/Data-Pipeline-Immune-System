# Secrets & Credentials Setup Guide — Data Pipeline Immune System

This guide explains **exactly where secrets live**, **how they are protected from leaking**, and **step-by-step instructions for obtaining each free credential**.

---

## 1. Where Are Credentials Stored in Your Project?

### In Local Development:
All local credentials live in one single file at the root of the project:
**`/.env`** (File path: [/.env](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/.env))

### Are Secrets Leaking to Git?
**NO — Zero secrets are leaking.**
1. `.env` is explicitly listed in [.gitignore](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/.gitignore):
   ```gitignore
   *.env
   .env
   .env.*
   !.env.example
   ```
2. Running `git status` or `git diff` will **never** track or display `.env`.
3. If `.env` is empty or credentials are not filled, all notification scripts automatically execute in **Safe Simulation (Dry-Run)** mode. Nothing breaks or fails.

### In Production (Google Cloud Platform):
In Cloud Run and production pipelines, secrets are stored in **Google Cloud Secret Manager**:
- Path: `projects/data-pipeline-immune-system/secrets/...`
- Injected at runtime via **Workload Identity** (IAM service accounts). No passwords or keys are saved on disk.

---

## 2. Step-by-Step Instructions: How to Get Each Credential

### Step A: Free Gmail App Password (For Daily Email Reports)
> [!NOTE]
> Do NOT use your regular Gmail account password. Google requires an **App Password** for SMTP.

1. Open your Google Account Security settings: **[https://myaccount.google.com/security](https://myaccount.google.com/security)**
2. Ensure **2-Step Verification** is turned **ON**.
3. In the search bar at the top, type **`App Passwords`** (or go to **[https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)**).
4. Enter an App Name: `Data Pipeline Immune System`.
5. Click **Create**.
6. Google will generate a **16-character code** (e.g. `abcd efgh ijkl mnop`).
7. Open [/.env](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/.env) and set:
   ```env
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=dhruvpratapsingh30.official2.o@gmail.com
   SMTP_SENDER=dhruvpratapsingh30.official2.o@gmail.com
   DAILY_REPORT_RECIPIENT=dhruvpratapsingh30.official2.o@gmail.com
   SMTP_PASSWORD=abcdefghijklmnop
   ```

---

### Step B: Google Cloud Platform (GCP) Credentials
To allow local Python scripts to query BigQuery and write to Cloud Storage:

1. Open your terminal on your Mac and run:
   ```bash
   gcloud auth application-default login
   ```
2. A browser window will open. Sign in with your Google account.
3. This creates your local credentials file at:
   `/Users/dhruvpratapsingh/.config/gcloud/application_default_credentials.json`
4. In [/.env](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/.env), ensure:
   ```env
   GCP_PROJECT=data-pipeline-immune-system
   GCP_REGION=us-central1
   GOOGLE_APPLICATION_CREDENTIALS=/Users/dhruvpratapsingh/.config/gcloud/application_default_credentials.json
   ```

---

### Step C: Free Hourly Mobile Alerts (Choose Option 1, 2, or 3)

#### Option 1: Telegram Bot (Recommended — 100% Free Forever, 1 Minute Setup)
> [!TIP]
> Telegram bots provide instant push notifications to your phone with sound, require zero credit card, and never expire.

1. Open the Telegram app on your phone or laptop.
2. Search for the official **`@BotFather`** account.
3. Send the command: `/newbot`
4. Follow the prompt to name your bot (e.g., `ImmuneAlertsBot`).
5. BotFather will provide an **HTTP API Token** (e.g. `7123456789:ABCdefGHIjklMNOpqrSTUvwxyz`).
6. Next, search for **`@userinfobot`** in Telegram and click **Start** to get your numeric **Chat ID** (e.g. `123456789`).
7. Start a conversation with your new bot by clicking its link and pressing **Start**.
8. In [/.env](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/.env), set:
   ```env
   TELEGRAM_BOT_TOKEN=7123456789:ABCdefGHIjklMNOpqrSTUvwxyz
   TELEGRAM_CHAT_ID=123456789
   ```

#### Option 2: Meta WhatsApp Cloud API (Official Free Tier — 1,000 Free Conversations/Month)
1. Go to **[https://developers.facebook.com/](https://developers.facebook.com/)** and log in.
2. Click **My Apps** ➔ **Create App**.
3. Select **Other** ➔ Select **Business** ➔ Name your app `Data Pipeline Immune System`.
4. In the App Dashboard, scroll down and click **Set up** under **WhatsApp**.
5. Under **WhatsApp** ➔ **API Setup**:
   - Copy the **Temporary access token** into `WHATSAPP_API_TOKEN`.
   - Copy the **Phone number ID** into `WHATSAPP_PHONE_NUMBER_ID`.
   - Add your personal phone number in the **To** field to receive test messages.
6. In [/.env](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/.env), set:
   ```env
   WHATSAPP_API_TOKEN=EAA...
   WHATSAPP_PHONE_NUMBER_ID=1029384756
   WHATSAPP_RECIPIENT=+919876543210
   ```

#### Option 3: ntfy.sh (100% Free Open-Source Push Notifications — Zero Signup)
1. Install the free **ntfy** app from Google Play or Apple App Store.
2. Subscribe to a topic name of your choice (e.g. `dpis-alerts-dpsingh`).
3. In [/.env](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/.env), set:
   ```env
   ENABLE_NTFY_PUSH=true
   NTFY_TOPIC=dpis-alerts-dpsingh
   ```

---

### Step D: AI Diagnosis Agent (Gemini 1.5)
1. Go to Google AI Studio: **[https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)**
2. Click **Create API Key**.
3. Select your project (`data-pipeline-immune-system`) or create a free key.
4. In [/.env](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/.env), set:
   ```env
   GEMINI_API_KEY=AIzaSy...
   ```

---

## 3. How to Test Your Credentials

Once you fill in [/.env](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/.env), test them with the CLI scripts:

### Test Email Delivery:
```bash
python3 scripts/send_daily_report.py --environment dev
```
- If SMTP password is set: Delivers real executive HTML report directly to your inbox.
- If SMTP password is empty: Executes safely in dry-run mode and logs what would be sent.

### Test Mobile Alert Delivery:
```bash
python3 scripts/send_hourly_whatsapp.py --status HEALTHY --score 99.2
```
- Dispatches hourly status pulse to your configured Telegram or Meta WhatsApp channel.
