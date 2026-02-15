# Porter Driver Analytics Agent

An automated AI agent that fetches Porter driver performance data from email, analyzes metrics, and sends comprehensive daily reports with insights and visualizations.

## 🚀 Features

- **Automated Email Integration**: Fetches Excel files from Gmail automatically
- **Comprehensive Analysis**: 
  - Driver performance metrics (orders, cancellations, idle time, cash collected)
  - Location-based performance comparison
  - Day-over-day trend analysis
- **Visual Reports**: Beautiful HTML reports with interactive charts
- **Automated Insights**: AI-generated insights and performance alerts
- **Email Delivery**: Sends formatted reports to stakeholders automatically

## 📋 Prerequisites

- Python 3.8 or higher
- Gmail account with App Password enabled
- Porter data Excel files received via email

## 🔧 Installation

### 1. Clone or Download the Project

```bash
cd porter-analytics-agent
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Email Settings

#### Create Configuration File

Copy the example configuration:

```bash
copy config\.env.example config\.env
```

#### Set Up Gmail App Password

1. Go to your Google Account: https://myaccount.google.com/
2. Navigate to **Security** → **2-Step Verification** (enable if not already)
3. Scroll to **App passwords**: https://myaccount.google.com/apppasswords
4. Generate a new app password for "Mail"
5. Copy the 16-character password

#### Edit config\.env

Open `config\.env` and fill in your details:

```env
# Your Gmail address where Porter data is received
EMAIL_ADDRESS=your-email@gmail.com

# Gmail App Password (16 characters, no spaces)
EMAIL_PASSWORD=your-app-password-here

# Email address that sends Porter data (already configured)
EMAIL_SENDER_FILTER=datainfra@theporter.in

# Recipients for the daily report (comma-separated)
REPORT_TO=manager@example.com,team@example.com
```

**Important**: Never commit the `.env` file to version control!

## 🎯 Usage

### Test Mode (Recommended First Run)

Test with your existing Excel file without sending emails:

```bash
python main.py --test-mode --input "C:\Users\anubh\Downloads\Porter analysis.xlsx" --no-fetch
```

This will:
- ✅ Process the Excel file
- ✅ Generate analysis and report
- ✅ Save report to `data/reports/`
- ❌ NOT fetch from email
- ❌ NOT send email report

### Production Mode

Run the full workflow (fetch from email, analyze, send report):

```bash
python main.py
```

This will:
1. Fetch latest Excel from email (from datainfra@theporter.in)
2. Process and analyze the data
3. Compare with previous day's data (if available)
4. Generate HTML report with charts
5. Send report via email to configured recipients
6. Archive data for future comparisons

### Manual Input Mode

Process a specific Excel file and send the report:

```bash
python main.py --input "path\to\your\file.xlsx" --no-fetch
```

## ⏰ Automation

### Windows Task Scheduler

1. Open **Task Scheduler**
2. Click **Create Basic Task**
3. Name: "Porter Analytics Daily Report"
4. Trigger: **Daily** at your preferred time (e.g., 9:00 AM)
5. Action: **Start a program**
   - Program: `python`
   - Arguments: `C:\Users\anubh\.gemini\antigravity\scratch\porter-analytics-agent\main.py`
   - Start in: `C:\Users\anubh\.gemini\antigravity\scratch\porter-analytics-agent`
6. Finish and test the task

### Alternative: Run on Demand

Simply double-click `main.py` or run from command line whenever needed.

## 📊 Report Contents

The generated report includes:

### Summary Metrics
- Total drivers
- Active drivers (meeting minimum order threshold)
- Number of regions

### Driver Performance
- 🏆 Top 10 performers (by orders completed)
- ⚠️ High cancellation rate drivers
- ⏱️ High idle time drivers
- Performance distribution charts

### Location Analysis
- Performance by geographic region
- Regional comparisons (orders, drivers, cash collected)
- Location-wise trends

### Day-over-Day Comparison
- Total orders change
- Cash collection change
- Regional performance changes
- Trend indicators

### Automated Insights
- Key performance indicators
- Alerts for drivers needing attention
- Recommendations for improvement

## ☁️ Cloud Deployment (GitHub Actions)

Run the agent 24/7 for free using GitHub Actions.

### 1. Create a GitHub Repository
1. Go to [GitHub.com](https://github.com) and create a new **Private** repository.
2. Push this code to the repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git push -u origin main
   ```

### 2. Configure Secrets
1. Go to your GitHub Repository **Settings** -> **Secrets and variables** -> **Actions**.
2. Click **New repository secret**.
3. Add the following secrets (copy values from your `.env`):
   - `EMAIL_ADDRESS`
   - `EMAIL_PASSWORD`
   - `REPORT_TO`
   - `EMAIL_SENDER_FILTER` (optional, defaults to datainfra@theporter.in)

### 3. Verification
- Go to the **Actions** tab in your repository.
- You see the "Porter Daily Analytics" workflow.
- You can click "Run workflow" to test it immediately.
- It will automatically run every day at 11:00 AM IST.

## 📁 Directory Structure

```
porter-analytics-agent/
├── config/
│   ├── .env.example          # Configuration template
│   └── .env                  # Your actual config (create this)
├── data/
│   ├── current/              # Today's downloaded Excel files
│   ├── historical/           # Archived data for comparisons
│   └── reports/              # Generated HTML reports
├── src/
│   ├── email_handler.py      # Email operations
│   ├── data_processor.py     # Data processing
│   ├── analyzer.py           # Performance analysis
│   └── report_generator.py   # Report generation
├── main.py                   # Main script
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## 🔍 Troubleshooting

### "No matching emails found"
- Check that `EMAIL_SENDER_FILTER` matches the sender address
- Verify you have unread emails from Porter
- Check `EMAIL_SUBJECT_FILTER` in config

### "Authentication failed"
- Ensure you're using an App Password, not your regular Gmail password
- Verify 2-Step Verification is enabled on your Google Account
- Check for typos in `EMAIL_ADDRESS` and `EMAIL_PASSWORD`

### "Failed to send report"
- Verify SMTP settings in config
- Check recipient email addresses in `REPORT_TO`
- Ensure App Password has correct permissions

### Charts not displaying
- Install kaleido: `pip install kaleido`
- Check that plotly is installed correctly

## ⚙️ Configuration Options

Edit `config/.env` to customize:

| Setting | Description | Default |
|---------|-------------|---------|
| `MIN_ORDERS_THRESHOLD` | Minimum orders to be "active" | 5 |
| `IDLE_HOURS_WARNING` | Idle hours threshold for alerts | 4 |
| `CANCELLATION_RATE_WARNING` | Cancellation % threshold | 15 |
| `ONLY_UNREAD` | Only process unread emails | true |
| `MARK_AS_READ` | Mark emails as read after processing | true |
| `DEBUG_MODE` | Enable detailed logging | false |

## 📝 Logs

All execution logs are saved to `porter_analytics.log` in the project directory.

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review logs in `porter_analytics.log`
3. Verify configuration in `config/.env`

## 📄 License

This project is for internal use. All Porter data should be handled according to your organization's data privacy policies.

---

**Built with ❤️ for automated Porter driver analytics**
