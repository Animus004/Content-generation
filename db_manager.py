#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Manager for Content Tracker
A complete SQLite database management system for tracking generated content ideas,
preventing duplicates, and managing continuation sequences.
"""

import sqlite3
import os
from typing import Optional, Tuple
from datetime import datetime


# Database configuration
DB_NAME = 'content_tracker.db'
DB_PATH = os.path.join(os.path.dirname(__file__), DB_NAME)


def setup_database() -> None:
    """
    Initialize the database connection and create the ideas_log table if it doesn't exist.
    Enhanced with comprehensive error handling and validation.
    
    Creates the content_tracker.db file and the ideas_log table with the following schema:
    - id: INTEGER PRIMARY KEY (auto-increment)
    - title: TEXT NOT NULL (for duplication checking)
    - niche: TEXT NOT NULL (content category)
    - continuation_day: INTEGER NOT NULL (sequence tracking)
    - created_at: TEXT (timestamp, default CURRENT_TIMESTAMP)
    - generation_date: TEXT (date only, YYYY-MM-DD format for daily logic)
    """
    try:
        # Validate database directory permissions
        db_dir = os.path.dirname(DB_PATH)
        if not os.access(db_dir, os.W_OK):
            raise PermissionError(f"No write permission to database directory: {db_dir}")
        
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Enable foreign keys and enhance database settings
            cursor.execute('PRAGMA foreign_keys = ON')
            cursor.execute('PRAGMA journal_mode = WAL')  # Better concurrency
            cursor.execute('PRAGMA synchronous = NORMAL')  # Balance safety and speed
            
            # Create the ideas_log table with enhanced daily tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ideas_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    niche TEXT NOT NULL,
                    continuation_day INTEGER NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    generation_date TEXT NOT NULL,
                    CHECK (continuation_day > 0),
                    CHECK (niche IN ('MMO', 'AI/Tech', 'Faceless'))
                )
            ''')
            
            # Add generation_date column if it doesn't exist (for existing databases)
            cursor.execute('''
                SELECT sql FROM sqlite_master WHERE type='table' AND name='ideas_log'
            ''')
            table_schema = cursor.fetchone()
            if table_schema and 'generation_date' not in table_schema[0]:
                cursor.execute('''
                    ALTER TABLE ideas_log ADD COLUMN generation_date TEXT
                ''')
                # Update existing records with today's date
                today = datetime.now().strftime('%Y-%m-%d')
                cursor.execute('''
                    UPDATE ideas_log SET generation_date = ? WHERE generation_date IS NULL
                ''', (today,))
            
            # Create indexes for faster lookups
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_title ON ideas_log(title)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_niche_date ON ideas_log(niche, generation_date)
            ''')
            
            # Create index for faster niche-based queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_niche_day ON ideas_log(niche, continuation_day)
            ''')
            
            conn.commit()
            print(f"✅ Database setup completed successfully: {DB_PATH}")
            
    except sqlite3.Error as e:
        print(f"❌ Database setup error: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error during database setup: {e}")
        raise


def log_idea(title: str, niche: str, continuation_day: int, time_slot: str = None) -> bool:
    """
    Insert a newly generated content idea into the ideas_log table with daily overwrite logic.
    
    Daily Logic Rules:
    - If generating multiple times in the same day: only keep the last generation (overwrite)
    - Cross-day progression is preserved: Day 2 will never overwrite Day 1
    - Same day overwrites maintain progression: Day 5 can be regenerated on the same day
    
    Args:
        title (str): The title of the content idea
        niche (str): The content niche/category
        continuation_day (int): The current day in the content sequence
        
    Returns:
        bool: True if insertion successful, False otherwise
        
    Raises:
        ValueError: If any required parameter is empty or invalid
        sqlite3.Error: If database operation fails
    """
    # Validate inputs
    if not title or not title.strip():
        raise ValueError("Title cannot be empty")
    if not niche or not niche.strip():
        raise ValueError("Niche cannot be empty")
    if continuation_day < 1:
        raise ValueError("Continuation day must be a positive integer")
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Get today's date
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Check if we have any ideas for this niche from today
            cursor.execute('''
                SELECT id, continuation_day FROM ideas_log 
                WHERE niche = ? AND generation_date = ?
            ''', (niche.strip(), today))
            
            existing_today = cursor.fetchall()
            
            if existing_today:
                # Delete all ideas from today for this niche (overwrite same day)
                cursor.execute('''
                    DELETE FROM ideas_log 
                    WHERE niche = ? AND generation_date = ?
                ''', (niche.strip(), today))
                print(f"🔄 Overwriting {len(existing_today)} existing ideas from today for {niche}")
            
            # Insert the new idea with today's date
            cursor.execute('''
                INSERT INTO ideas_log (title, niche, continuation_day, created_at, generation_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (title.strip(), niche.strip(), continuation_day, datetime.now().isoformat(), today))
            
            conn.commit()
            
            # Get the ID of the inserted record
            idea_id = cursor.lastrowid
            print(f"✅ Idea logged successfully (ID: {idea_id}): {title[:50]}...")
            
            return True
            
    except sqlite3.Error as e:
        print(f"❌ Database error while logging idea: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error while logging idea: {e}")
        return False


def get_current_day(niche: str) -> int:
    """
    Retrieve the highest continuation_day for a specific niche with daily logic.
    
    Daily Logic: Only considers historical days (not today) to determine next day number.
    This ensures that multiple generations on the same day don't increment the day counter.
    
    Args:
        niche (str): The content niche/category to query
        
    Returns:
        int: The highest continuation_day for the niche from previous days, or 0 if no records exist
        
    Raises:
        ValueError: If niche is empty
        sqlite3.Error: If database operation fails
    """
    if not niche or not niche.strip():
        raise ValueError("Niche cannot be empty")
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Get today's date
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Query for the maximum continuation_day for the specified niche
            # EXCLUDE today's entries to prevent day increment on same-day regeneration
            cursor.execute('''
                SELECT MAX(continuation_day) 
                FROM ideas_log 
                WHERE niche = ? AND generation_date != ?
            ''', (niche.strip(), today))
            
            result = cursor.fetchone()
            
            # Return the max day or 0 if no records exist
            max_day = result[0] if result[0] is not None else 0
            
            # Check if we have any entries from today for this niche
            cursor.execute('''
                SELECT continuation_day FROM ideas_log 
                WHERE niche = ? AND generation_date = ?
                LIMIT 1
            ''', (niche.strip(), today))
            
            today_result = cursor.fetchone()
            
            if today_result:
                # If we have entries from today, return the day from today's entry
                current_day = today_result[0] - 1  # Subtract 1 because we'll add 1 later
                print(f"📊 Current day for '{niche}': {current_day} (continuing today's Day {today_result[0]})")
            else:
                # No entries from today, return historical max
                current_day = max_day
                print(f"📊 Current day for '{niche}': {current_day} (from historical records)")
            
            return current_day
            
    except sqlite3.Error as e:
        print(f"❌ Database error while getting current day: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error while getting current day: {e}")
        raise


def check_for_duplication(title: str) -> bool:
    """
    Check if a title already exists in the database to prevent duplicates.
    
    Args:
        title (str): The title to check for duplication
        
    Returns:
        bool: True if the title already exists, False otherwise
        
    Raises:
        ValueError: If title is empty
        sqlite3.Error: If database operation fails
    """
    if not title or not title.strip():
        raise ValueError("Title cannot be empty")
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Check for exact title match (case-insensitive)
            cursor.execute('''
                SELECT COUNT(*) 
                FROM ideas_log 
                WHERE LOWER(title) = LOWER(?)
            ''', (title.strip(),))
            
            result = cursor.fetchone()
            is_duplicate = result[0] > 0
            
            if is_duplicate:
                print(f"⚠️ Duplicate detected: '{title[:50]}...'")
            else:
                print(f"✅ Title is unique: '{title[:50]}...'")
                
            return is_duplicate
            
    except sqlite3.Error as e:
        print(f"❌ Database error while checking duplication: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error while checking duplication: {e}")
        raise


def get_all_ideas(niche: Optional[str] = None, limit: Optional[int] = None) -> list:
    """
    Retrieve all ideas from the database, optionally filtered by niche.
    
    Args:
        niche (Optional[str]): Filter by specific niche, or None for all niches
        limit (Optional[int]): Maximum number of records to return, or None for all
        
    Returns:
        list: List of tuples containing (id, title, niche, continuation_day, created_at)
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            if niche:
                query = '''
                    SELECT id, title, niche, continuation_day, created_at 
                    FROM ideas_log 
                    WHERE niche = ?
                    ORDER BY continuation_day DESC, created_at DESC
                '''
                params = (niche.strip(),)
            else:
                query = '''
                    SELECT id, title, niche, continuation_day, created_at 
                    FROM ideas_log 
                    ORDER BY created_at DESC
                '''
                params = ()
            
            if limit:
                query += f' LIMIT {limit}'
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            print(f"📋 Retrieved {len(results)} ideas" + (f" for niche '{niche}'" if niche else ""))
            return results
            
    except sqlite3.Error as e:
        print(f"❌ Database error while retrieving ideas: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error while retrieving ideas: {e}")
        return []


def get_database_stats() -> dict:
    """
    Get statistics about the content database.
    
    Returns:
        dict: Statistics including total ideas, ideas per niche, and date range
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Total ideas count
            cursor.execute('SELECT COUNT(*) FROM ideas_log')
            total_ideas = cursor.fetchone()[0]
            
            # Ideas per niche
            cursor.execute('''
                SELECT niche, COUNT(*) as count, MAX(continuation_day) as max_day
                FROM ideas_log 
                GROUP BY niche 
                ORDER BY count DESC
            ''')
            niche_stats = cursor.fetchall()
            
            # Date range
            cursor.execute('''
                SELECT MIN(created_at) as first_idea, MAX(created_at) as latest_idea
                FROM ideas_log
            ''')
            date_range = cursor.fetchone()
            
            return {
                'total_ideas': total_ideas,
                'niche_breakdown': niche_stats,
                'first_idea_date': date_range[0],
                'latest_idea_date': date_range[1]
            }
            
    except sqlite3.Error as e:
        print(f"❌ Database error while getting stats: {e}")
        return {}


def main():
    """
    Demonstrate the database functionality with setup and basic operations.
    
    This function:
    1. Sets up the database and creates tables
    2. Demonstrates getting current day for 'MMO' niche (returns 0 if empty)
    3. Shows example usage of other functions
    """
    print("🚀 Content Tracker Database Manager")
    print("=" * 50)
    
    try:
        # Initialize the database
        print("\n1. Setting up database...")
        setup_database()
        
        # Demonstrate getting current day for MMO (should return 0 if empty)
        print("\n2. Checking current day for 'MMO' niche...")
        current_day = get_current_day('MMO')
        print(f"Current continuation day for 'MMO': {current_day}")
        
        # Demonstrate duplication checking with a test title
        print("\n3. Testing duplication check...")
        test_title = "Test Title for Duplication Check"
        is_duplicate = check_for_duplication(test_title)
        print(f"Is '{test_title}' a duplicate? {is_duplicate}")
        
        # Example: Add a test idea if database is empty
        if current_day == 0:
            print("\n4. Adding example idea to demonstrate functionality...")
            success = log_idea(
                title="5 Quick Investment Tips for Absolute Beginners",
                niche="MMO",
                continuation_day=1
            )
            
            if success:
                # Check the day again
                new_day = get_current_day('MMO')
                print(f"New current day for 'MMO': {new_day}")
        
        # Show database statistics
        print("\n5. Database Statistics:")
        stats = get_database_stats()
        if stats:
            print(f"Total ideas: {stats['total_ideas']}")
            print("Ideas per niche:")
            for niche, count, max_day in stats.get('niche_breakdown', []):
                print(f"  - {niche}: {count} ideas (up to day {max_day})")
        
        print("\n✅ Database manager demonstration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())