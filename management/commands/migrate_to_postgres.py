"""
Bonjour Classe Web App - Data Migration Script

This script helps you migrate data from SQLite to PostgreSQL.
It uses Django's dumpdata/loaddata commands to export and import data.
"""

import os
import subprocess
import sys
import json
from datetime import datetime

def ensure_directory(directory):
    """Make sure the directory exists."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")

def run_command(command, error_message="Command failed"):
    """Run a shell command and handle errors."""
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error: {error_message}")
        print(f"Command: {' '.join(command)}")
        print(f"Error details: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return None

def backup_sqlite_data():
    """Backup all data from SQLite database."""
    print("Backing up data from SQLite database...")
    
    # Define directories
    backup_dir = os.path.join('data_backup', datetime.now().strftime("%Y%m%d_%H%M%S"))
    ensure_directory(backup_dir)
    
    # Get list of installed apps from Django
    apps_command = ["python", "backend/manage.py", "dumpdata", "--list-apps"]
    apps_output = run_command(apps_command, "Failed to list apps")
    
    if not apps_output:
        return False
    
    # Parse the output to get app names
    apps = [line.strip() for line in apps_output.splitlines() if line.strip()]
    
    # Export each app individually to avoid issues with dependencies
    for app in apps:
        if app in ['contenttypes', 'auth.permission', 'admin', 'sessions']:
            continue  # Skip these as they can cause issues
        
        print(f"Backing up {app}...")
        output_file = os.path.join(backup_dir, f"{app.replace('.', '_')}.json")
        
        dump_command = [
            "python", "backend/manage.py", "dumpdata", 
            "--indent", "4", 
            "--output", output_file,
            app
        ]
        run_command(dump_command, f"Failed to dump data for {app}")
    
    print(f"Data backup completed in {backup_dir}")
    return backup_dir

def update_db_settings_for_postgres():
    """Update Django settings to use PostgreSQL."""
    # Check if python production.py exists, if so run it
    if os.path.exists("production.py"):
        print("Updating settings to use PostgreSQL...")
        run_command(["python", "production.py"], "Failed to update settings")
    else:
        print("Warning: production.py not found. Make sure to update your settings.py manually!")

def restore_data_to_postgres(backup_dir):
    """Restore backed up data to PostgreSQL."""
    print("\nRestoring data to PostgreSQL...")
    print("First, let's run migrations to create the schema...")
    
    run_command(["python", "backend/manage.py", "migrate"], "Failed to run migrations")
    
    # Get all backup JSON files
    backup_files = []
    for filename in os.listdir(backup_dir):
        if filename.endswith('.json'):
            backup_files.append(os.path.join(backup_dir, filename))
    
    # Sort them to respect dependencies
    backup_files = sorted(backup_files)
    
    # Special handling for certain apps that should be loaded first
    priority_apps = ['userauths_user', 'auth_group']
    for priority in priority_apps:
        for i, filepath in enumerate(backup_files):
            if priority in os.path.basename(filepath):
                # Move to the front of the list
                backup_files.insert(0, backup_files.pop(i))
                break
    
    # Load each file
    for filepath in backup_files:
        app_name = os.path.basename(filepath).replace('.json', '')
        print(f"Restoring {app_name}...")
        
        # First try to load with --app option
        load_command = [
            "python", "backend/manage.py", "loaddata", filepath
        ]
        run_command(load_command, f"Failed to load data for {app_name}")
    
    print("Data restoration completed")

def main():
    """Main function to execute the migration process."""
    print("Bonjour Classe Web App - SQLite to PostgreSQL Migration")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("backend/manage.py"):
        print("Error: This script should be run from the project root directory.")
        print("Make sure you can see 'backend/manage.py' from your current location.")
        return
    
    # Check if psycopg2 is installed
    try:
        import psycopg2
        print("✓ psycopg2 is installed.")
    except ImportError:
        print("Error: psycopg2 is not installed. Please install it with:")
        print("pip install psycopg2-binary")
        return
    
    # Backup data from SQLite
    backup_dir = backup_sqlite_data()
    if not backup_dir:
        print("Failed to backup data. Aborting migration.")
        return
    
    # Update settings to use PostgreSQL
    update_db_settings_for_postgres()
    
    # Confirm PostgreSQL setup
    print("\nBefore continuing, please make sure your PostgreSQL database is set up:")
    print("1. PostgreSQL is installed and running")
    print("2. A database has been created")
    print("3. The user has appropriate permissions")
    print("4. Your .env file has been updated with PostgreSQL credentials")
    
    confirm = input("\nDo you want to proceed with migrating data to PostgreSQL? (y/n): ")
    if confirm.lower() != 'y':
        print("Migration aborted. Your data backup is still available at:", backup_dir)
        return
    
    # Restore data to PostgreSQL
    restore_data_to_postgres(backup_dir)
    
    print("\nMigration completed successfully!")
    print("=" * 50)
    print("Next steps:")
    print("1. Test your application to ensure it works with PostgreSQL")
    print("2. Update your production deployment configuration")
    print("3. Consider running 'python manage.py collectstatic' for production")

if __name__ == "__main__":
    main()
