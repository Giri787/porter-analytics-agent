"""
Main Orchestration Script
Coordinates the entire Porter analytics workflow.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
import argparse
import shutil

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from email_handler import EmailHandler
from data_processor import DataProcessor
from analyzer import PorterAnalyzer
from integrity_analyzer import IntegrityAnalyzer
from monthly_relational_analyzer import MonthlyRelationalAnalyzer
from report_generator import ReportGenerator


def setup_logging(debug_mode: bool = False):
    """Setup logging configuration."""
    log_level = logging.DEBUG if debug_mode else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('porter_analytics.log'),
            logging.StreamHandler()
        ]
    )


def load_config():
    """Load configuration from .env file or environment variables."""
    config_path = Path('config/.env')
    if not config_path.exists():
        config_path = Path('.env')
    
    if config_path.exists():
        load_dotenv(config_path)
    else:
        load_dotenv()
    
    config = {
        'EMAIL_ADDRESS': os.getenv('EMAIL_ADDRESS', ''),
        'EMAIL_PASSWORD': os.getenv('EMAIL_PASSWORD', 'oauth2'),
        'IMAP_SERVER': os.getenv('IMAP_SERVER', 'imap.gmail.com'),
        'IMAP_PORT': os.getenv('IMAP_PORT', '993'),
        'SMTP_SERVER': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        'SMTP_PORT': os.getenv('SMTP_PORT', '587'),
        'EMAIL_SENDER_FILTER': os.getenv('EMAIL_SENDER_FILTER', 'datareports@theporter.in'),
        'EMAIL_SUBJECT_FILTER': os.getenv('EMAIL_SUBJECT_FILTER', '3W - EV daily report'),
        'REPORT_TO': os.getenv('REPORT_TO', ''),
        'ONLY_UNREAD': os.getenv('ONLY_UNREAD', 'false'),
        'MARK_AS_READ': os.getenv('MARK_AS_READ', 'true'),
        'REPORT_FROM_NAME': os.getenv('REPORT_FROM_NAME', 'Porter Analytics Agent'),
        'REPORT_SUBJECT': os.getenv('REPORT_SUBJECT', 'Daily Porter Driver Performance Report - {date}'),
        'MIN_ORDERS_THRESHOLD': os.getenv('MIN_ORDERS_THRESHOLD', '5'),
        'IDLE_HOURS_WARNING': os.getenv('IDLE_HOURS_WARNING', '4'),
        'CANCELLATION_RATE_WARNING': os.getenv('CANCELLATION_RATE_WARNING', '15'),
        'DEBUG_MODE': os.getenv('DEBUG_MODE', 'false'),
    }
    
    return config


def get_previous_day_data(historical_dir: Path):
    """
    Find and load the most recent historical data file.
    
    Args:
        historical_dir: Path to historical data directory
        
    Returns:
        DataFrame of previous day's data, or None if not found
    """
    try:
        # Find all data files in historical directory
        data_files = list(historical_dir.glob('*.xlsx')) + list(historical_dir.glob('*.csv'))
        
        if not data_files:
            logging.info("No historical data found for comparison")
            return None
        
        # Get the most recent file
        latest_file = max(data_files, key=lambda p: p.stat().st_mtime)
        logging.info(f"Loading previous data from: {latest_file}")
        
        processor = DataProcessor()
        if processor.load_data(str(latest_file)):
            processor.filter_vehicle_type() # Ensure we filter historical data too
            processor.clean_data()
            return processor.get_dataframe()
        
        return None
        
    except Exception as e:
        logging.error(f"Error loading previous day data: {str(e)}")
        return None


def archive_current_data(current_file: Path, historical_dir: Path):
    """
    Archive current data file to historical directory.
    
    Args:
        current_file: Path to current data file
        historical_dir: Path to historical directory
    """
    try:
        timestamp = datetime.now().strftime('%Y%m%d')
        ext = current_file.suffix
        archive_name = f"porter_data_{timestamp}{ext}"
        archive_path = historical_dir / archive_name
        
        shutil.copy2(current_file, archive_path)
        logging.info(f"Archived data to: {archive_path}")
        
    except Exception as e:
        logging.error(f"Error archiving data: {str(e)}")


def main(test_mode: bool = False, input_file: str = None, fetch_email: bool = True):
    """
    Main execution function.
    
    Args:
        test_mode: If True, run in test mode (don't send emails)
        input_file: Path to input Excel/CSV file (for testing)
        fetch_email: If True, fetch from email; if False, use input_file
    """
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Porter Analytics Agent - Starting")
    logger.info("=" * 60)
    
    try:
        # Load configuration
        config = load_config()
        setup_logging(config['DEBUG_MODE'].lower() == 'true')
        
        # Setup directories
        base_dir = Path(__file__).parent
        data_dir = base_dir / 'data'
        current_dir = data_dir / 'current'
        historical_dir = data_dir / 'historical'
        reports_dir = data_dir / 'reports'
        
        # Create directories if they don't exist
        for dir_path in [current_dir, historical_dir, reports_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Get data file
        data_file = None
        
        if input_file:
            # Use provided input file
            logger.info(f"Using input file: {input_file}")
            data_file = input_file
        elif fetch_email:
            # Fetch from email
            logger.info("Fetching latest report from email...")
            email_handler = EmailHandler(config)
            data_file = email_handler.fetch_latest_report(str(current_dir))
            
            if not data_file:
                logger.error("No data file found in email. Exiting.")
                return False
        else:
            logger.error("No input file specified and fetch_email is False")
            return False
        
        # Step 2: Process data
        logger.info("Processing data...")
        processor = DataProcessor()
        
        if not processor.load_data(data_file):
            logger.error("Failed to load data file")
            return False
        
        # Filter 3-wheelers
        if not processor.filter_vehicle_type("3 Wheeler Electric"):
             logger.warning("Vehicle type filtering failed or skipped")

        if not processor.clean_data():
            logger.error("Failed to clean data")
            return False
        
        current_df = processor.get_dataframe()
        logger.info(f"Processed {len(current_df)} driver records (4-wheelers only)")
        
        # Step 3: Load previous day's data
        logger.info("Loading previous day's data for comparison...")
        previous_df = get_previous_day_data(historical_dir)
        
        # Step 4: Analyze data
        logger.info("Analyzing performance metrics...")
        analyzer = PorterAnalyzer(current_df, config)
        
        driver_perf = analyzer.analyze_driver_performance()
        location_perf = analyzer.analyze_location_performance()
        
        if previous_df is not None:
            dod_comparison = analyzer.compare_with_previous_day(previous_df)
        else:
            logger.info("No previous data available for comparison")
        
        insights = analyzer.generate_insights()
        
        # Step 4.5: Integrity & Productivity Analysis
        logger.info("Running advanced integrity analysis...")
        integrity_analyzer = IntegrityAnalyzer(current_df, config)
        integrity_results = integrity_analyzer.run_analysis()
        
        # Step 4.8: Monthly & Relational Analytics
        logger.info("Running 1-2 month relational and shift timing analytics...")
        monthly_analyzer = MonthlyRelationalAnalyzer(current_df, config)
        monthly_results = monthly_analyzer.run_full_analysis()
        
        # Step 5: Generate report
        logger.info("Generating report...")
        report_date = datetime.now().strftime('%Y-%m-%d')
        
        report_gen = ReportGenerator(
            analyzer.get_all_results(), 
            insights,
            integrity_results,
            monthly_results
        )
        
        html_report = report_gen.generate_html_report(report_date)
        
        # Save report to file
        report_filename = f"porter_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        report_path = reports_dir / report_filename
        report_gen.save_report(str(report_path), html_report)
        
        logger.info(f"Report saved to: {report_path}")
        
        # Step 6: Send email report
        if not test_mode and fetch_email:
            logger.info("Sending email report...")
            
            recipients = [email.strip() for email in config['REPORT_TO'].split(',')]
            subject = config['REPORT_SUBJECT'].format(date=report_date)
            
            email_handler = EmailHandler(config)
            success = email_handler.send_report(
                recipients=recipients,
                subject=subject,
                html_content=html_report,
                from_name=config['REPORT_FROM_NAME']
            )
            
            if success:
                logger.info("✅ Report sent successfully!")
            else:
                logger.error("❌ Failed to send report")
        else:
            logger.info("Test mode - skipping email send")
            logger.info(f"📄 Report available at: {report_path}")
        
        # Step 7: Archive current data
        if fetch_email and not test_mode:
            logger.info("Archiving current data...")
            archive_current_data(Path(data_file), historical_dir)
        
        logger.info("=" * 60)
        logger.info("Porter Analytics Agent - Completed Successfully")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Porter Driver Analytics Agent')
    parser.add_argument('--test-mode', action='store_true', 
                       help='Run in test mode (no email sending)')
    parser.add_argument('--input', type=str, 
                       help='Path to input Excel file (for testing)')
    parser.add_argument('--no-fetch', action='store_true',
                       help='Do not fetch from email (use --input instead)')
    
    args = parser.parse_args()
    
    success = main(
        test_mode=args.test_mode,
        input_file=args.input,
        fetch_email=not args.no_fetch
    )
    
    sys.exit(0 if success else 1)
