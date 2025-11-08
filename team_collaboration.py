# -*- coding: utf-8 -*-
"""
Team Collaboration System for AI Content Generator
Production-ready team management with invitations, roles, and project sharing
"""

import sqlite3
import uuid
import hashlib
import os
import smtplib
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Database path
DB_NAME = 'content_tracker_users_niche.db'
DB_PATH = os.path.join(os.path.dirname(__file__), DB_NAME)

def setup_team_database():
    """Initialize team collaboration tables with enhanced error handling"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Enable foreign keys for data integrity
            cursor.execute('PRAGMA foreign_keys = ON')
            
            # Teams table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS teams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id TEXT UNIQUE NOT NULL,
                    team_name TEXT NOT NULL,
                    description TEXT,
                    owner_id TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    max_members INTEGER DEFAULT 10,
                    plan_type TEXT DEFAULT 'free',
                    FOREIGN KEY (owner_id) REFERENCES auth_users (user_id)
                )
            ''')
            
            # Team members table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS team_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT DEFAULT 'member',
                    joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    invited_by TEXT,
                    is_active INTEGER DEFAULT 1,
                    permissions TEXT DEFAULT 'read,generate',
                    FOREIGN KEY (team_id) REFERENCES teams (team_id),
                    FOREIGN KEY (user_id) REFERENCES auth_users (user_id),
                    UNIQUE(team_id, user_id)
                )
            ''')
            
            # Team invitations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS team_invitations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invitation_id TEXT UNIQUE NOT NULL,
                    team_id TEXT NOT NULL,
                    invited_email TEXT NOT NULL,
                    invited_by TEXT NOT NULL,
                    invitation_token TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    role TEXT DEFAULT 'member',
                    permissions TEXT DEFAULT 'read,generate',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    expires_at TEXT NOT NULL,
                    accepted_at TEXT,
                    FOREIGN KEY (team_id) REFERENCES teams (team_id),
                    FOREIGN KEY (invited_by) REFERENCES auth_users (user_id)
                )
            ''')
            
            # Team projects table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS team_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT UNIQUE NOT NULL,
                    team_id TEXT NOT NULL,
                    project_name TEXT NOT NULL,
                    description TEXT,
                    created_by TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    niches TEXT,
                    project_type TEXT DEFAULT 'content_generation',
                    FOREIGN KEY (team_id) REFERENCES teams (team_id),
                    FOREIGN KEY (created_by) REFERENCES auth_users (user_id)
                )
            ''')
            
            # Shared content generations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shared_generations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    generation_id TEXT UNIQUE NOT NULL,
                    project_id TEXT NOT NULL,
                    team_id TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    generation_data TEXT NOT NULL,
                    ideas_count INTEGER DEFAULT 0,
                    niches_used TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_public INTEGER DEFAULT 0,
                    likes_count INTEGER DEFAULT 0,
                    comments_count INTEGER DEFAULT 0,
                    FOREIGN KEY (project_id) REFERENCES team_projects (project_id),
                    FOREIGN KEY (team_id) REFERENCES teams (team_id),
                    FOREIGN KEY (created_by) REFERENCES auth_users (user_id)
                )
            ''')
            
            # Team activity log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS team_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    activity_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (team_id) REFERENCES teams (team_id),
                    FOREIGN KEY (user_id) REFERENCES auth_users (user_id)
                )
            ''')
            
            # Team comments/feedback
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS generation_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comment_id TEXT UNIQUE NOT NULL,
                    generation_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    comment_text TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_edited INTEGER DEFAULT 0,
                    parent_comment_id TEXT,
                    FOREIGN KEY (generation_id) REFERENCES shared_generations (generation_id),
                    FOREIGN KEY (user_id) REFERENCES auth_users (user_id)
                )
            ''')
            
            conn.commit()
            print("✅ Team collaboration database setup completed")
            
    except Exception as e:
        print(f"❌ Team database setup error: {e}")

# TEAM MANAGEMENT FUNCTIONS

def create_team(owner_id: str, team_name: str, description: str = "", max_members: int = 10) -> Tuple[bool, str, Optional[str]]:
    """Create a new team"""
    try:
        if len(team_name.strip()) < 3:
            return False, "Team name must be at least 3 characters long", None
            
        team_id = str(uuid.uuid4())
        
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Check if user already has a team with this name
            cursor.execute('SELECT team_name FROM teams WHERE owner_id = ? AND team_name = ?', (owner_id, team_name))
            if cursor.fetchone():
                return False, "You already have a team with this name", None
            
            # Create team
            cursor.execute('''
                INSERT INTO teams (team_id, team_name, description, owner_id, max_members)
                VALUES (?, ?, ?, ?, ?)
            ''', (team_id, team_name.strip(), description, owner_id, max_members))
            
            # Add owner as admin member
            cursor.execute('''
                INSERT INTO team_members (team_id, user_id, role, permissions)
                VALUES (?, ?, 'admin', 'read,write,invite,manage')
            ''', (team_id, owner_id))
            
            # Log activity
            log_team_activity(team_id, owner_id, "team_created", f"Team '{team_name}' created")
            
            conn.commit()
            return True, f"Team '{team_name}' created successfully!", team_id
            
    except Exception as e:
        return False, f"Error creating team: {str(e)}", None

def invite_team_member(team_id: str, inviter_id: str, email: str, role: str = "member") -> Tuple[bool, str]:
    """Invite a user to join the team"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Check if inviter has permission
            cursor.execute('''
                SELECT role, permissions FROM team_members 
                WHERE team_id = ? AND user_id = ? AND is_active = 1
            ''', (team_id, inviter_id))
            
            inviter_info = cursor.fetchone()
            if not inviter_info or 'invite' not in inviter_info[1]:
                return False, "You don't have permission to invite members"
            
            # Check if email is already invited or member
            cursor.execute('''
                SELECT status FROM team_invitations 
                WHERE team_id = ? AND invited_email = ? AND status = 'pending'
            ''', (team_id, email))
            
            if cursor.fetchone():
                return False, "User already has a pending invitation"
            
            # Check if already a member
            cursor.execute('''
                SELECT u.email FROM team_members tm
                JOIN auth_users u ON tm.user_id = u.user_id
                WHERE tm.team_id = ? AND u.email = ? AND tm.is_active = 1
            ''', (team_id, email))
            
            if cursor.fetchone():
                return False, "User is already a team member"
            
            # Create invitation
            invitation_id = str(uuid.uuid4())
            invitation_token = hashlib.sha256(f"{invitation_id}{email}{datetime.now().isoformat()}".encode()).hexdigest()
            expires_at = (datetime.now() + timedelta(days=7)).isoformat()
            
            permissions = "read,generate" if role == "member" else "read,generate,invite"
            
            cursor.execute('''
                INSERT INTO team_invitations (
                    invitation_id, team_id, invited_email, invited_by, 
                    invitation_token, role, permissions, expires_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (invitation_id, team_id, email, inviter_id, invitation_token, role, permissions, expires_at))
            
            # Get team name for activity log
            cursor.execute('SELECT team_name FROM teams WHERE team_id = ?', (team_id,))
            team_name = cursor.fetchone()[0]
            
            log_team_activity(team_id, inviter_id, "member_invited", f"Invited {email} to join team")
            
            conn.commit()
            
            # TODO: Send email invitation (implement email service)
            return True, f"Invitation sent to {email}. They have 7 days to accept."
            
    except Exception as e:
        return False, f"Error sending invitation: {str(e)}"

def accept_team_invitation(invitation_token: str, user_id: str) -> Tuple[bool, str]:
    """Accept a team invitation"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Find and validate invitation
            cursor.execute('''
                SELECT invitation_id, team_id, role, permissions, expires_at, invited_email
                FROM team_invitations 
                WHERE invitation_token = ? AND status = 'pending'
            ''', (invitation_token,))
            
            invitation = cursor.fetchone()
            if not invitation:
                return False, "Invalid or expired invitation"
            
            invitation_id, team_id, role, permissions, expires_at, invited_email = invitation
            
            # Check if expired
            if datetime.fromisoformat(expires_at) < datetime.now():
                return False, "Invitation has expired"
            
            # Verify user email matches invitation
            cursor.execute('SELECT email FROM auth_users WHERE user_id = ?', (user_id,))
            user_email = cursor.fetchone()
            if not user_email or user_email[0] != invited_email:
                return False, "Invitation email doesn't match your account"
            
            # Add to team
            cursor.execute('''
                INSERT INTO team_members (team_id, user_id, role, permissions)
                VALUES (?, ?, ?, ?)
            ''', (team_id, user_id, role, permissions))
            
            # Update invitation status
            cursor.execute('''
                UPDATE team_invitations 
                SET status = 'accepted', accepted_at = ?
                WHERE invitation_id = ?
            ''', (datetime.now().isoformat(), invitation_id))
            
            # Get team name
            cursor.execute('SELECT team_name FROM teams WHERE team_id = ?', (team_id,))
            team_name = cursor.fetchone()[0]
            
            log_team_activity(team_id, user_id, "member_joined", f"Joined the team")
            
            conn.commit()
            return True, f"Successfully joined team '{team_name}'!"
            
    except Exception as e:
        return False, f"Error accepting invitation: {str(e)}"

# PROJECT MANAGEMENT FUNCTIONS

def create_team_project(team_id: str, creator_id: str, project_name: str, description: str = "", niches: str = "") -> Tuple[bool, str, Optional[str]]:
    """Create a new team project"""
    try:
        # Check permission
        if not has_team_permission(team_id, creator_id, "write"):
            return False, "You don't have permission to create projects", None
            
        project_id = str(uuid.uuid4())
        
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO team_projects (project_id, team_id, project_name, description, created_by, niches)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (project_id, team_id, project_name, description, creator_id, niches))
            
            log_team_activity(team_id, creator_id, "project_created", f"Created project '{project_name}'")
            
            conn.commit()
            return True, f"Project '{project_name}' created successfully!", project_id
            
    except Exception as e:
        return False, f"Error creating project: {str(e)}", None

def share_generation_to_team(team_id: str, project_id: str, user_id: str, generation_data: str, ideas_count: int, niches_used: str) -> Tuple[bool, str]:
    """Share a content generation with the team"""
    try:
        generation_id = str(uuid.uuid4())
        
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO shared_generations (
                    generation_id, project_id, team_id, created_by, 
                    generation_data, ideas_count, niches_used
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (generation_id, project_id, team_id, user_id, generation_data, ideas_count, niches_used))
            
            log_team_activity(team_id, user_id, "generation_shared", f"Shared {ideas_count} content ideas")
            
            conn.commit()
            return True, "Content shared with team successfully!"
            
    except Exception as e:
        return False, f"Error sharing content: {str(e)}"

# UTILITY FUNCTIONS

def get_user_teams(user_id: str) -> List[Dict]:
    """Get all teams user is a member of"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT t.team_id, t.team_name, t.description, tm.role, tm.permissions, t.owner_id,
                       (SELECT COUNT(*) FROM team_members WHERE team_id = t.team_id AND is_active = 1) as member_count
                FROM teams t
                JOIN team_members tm ON t.team_id = tm.team_id
                WHERE tm.user_id = ? AND tm.is_active = 1 AND t.is_active = 1
                ORDER BY t.created_at DESC
            ''', (user_id,))
            
            teams = []
            for row in cursor.fetchall():
                teams.append({
                    'team_id': row[0],
                    'team_name': row[1],
                    'description': row[2],
                    'role': row[3],
                    'permissions': row[4].split(','),
                    'is_owner': row[5] == user_id,
                    'member_count': row[6]
                })
            
            return teams
            
    except Exception as e:
        print(f"Error getting user teams: {e}")
        return []

def get_team_projects(team_id: str, user_id: str) -> List[Dict]:
    """Get all projects for a team"""
    try:
        # Check if user is team member
        if not is_team_member(team_id, user_id):
            return []
            
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT p.project_id, p.project_name, p.description, p.created_by, p.created_at, p.niches,
                       u.username as creator_name,
                       (SELECT COUNT(*) FROM shared_generations WHERE project_id = p.project_id) as generation_count
                FROM team_projects p
                JOIN auth_users u ON p.created_by = u.user_id
                WHERE p.team_id = ? AND p.status = 'active'
                ORDER BY p.created_at DESC
            ''', (team_id,))
            
            projects = []
            for row in cursor.fetchall():
                projects.append({
                    'project_id': row[0],
                    'project_name': row[1],
                    'description': row[2],
                    'created_by': row[3],
                    'created_at': row[4],
                    'niches': row[5],
                    'creator_name': row[6],
                    'generation_count': row[7]
                })
            
            return projects
            
    except Exception as e:
        print(f"Error getting team projects: {e}")
        return []

def get_shared_generations(project_id: str, user_id: str) -> List[Dict]:
    """Get shared generations for a project"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Check if user has access to this project
            cursor.execute('''
                SELECT tm.user_id FROM team_projects p
                JOIN team_members tm ON p.team_id = tm.team_id
                WHERE p.project_id = ? AND tm.user_id = ? AND tm.is_active = 1
            ''', (project_id, user_id))
            
            if not cursor.fetchone():
                return []
            
            cursor.execute('''
                SELECT sg.generation_id, sg.generation_data, sg.ideas_count, sg.niches_used, 
                       sg.created_at, sg.likes_count, sg.comments_count,
                       u.username as creator_name
                FROM shared_generations sg
                JOIN auth_users u ON sg.created_by = u.user_id
                WHERE sg.project_id = ?
                ORDER BY sg.created_at DESC
            ''', (project_id,))
            
            generations = []
            for row in cursor.fetchall():
                generations.append({
                    'generation_id': row[0],
                    'generation_data': row[1],
                    'ideas_count': row[2],
                    'niches_used': row[3],
                    'created_at': row[4],
                    'likes_count': row[5],
                    'comments_count': row[6],
                    'creator_name': row[7]
                })
            
            return generations
            
    except Exception as e:
        print(f"Error getting shared generations: {e}")
        return []

def has_team_permission(team_id: str, user_id: str, permission: str) -> bool:
    """Check if user has specific permission in team"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT permissions FROM team_members
                WHERE team_id = ? AND user_id = ? AND is_active = 1
            ''', (team_id, user_id))
            
            result = cursor.fetchone()
            if result:
                permissions = result[0].split(',')
                return permission in permissions or 'manage' in permissions
            
            return False
            
    except Exception as e:
        print(f"Error checking permission: {e}")
        return False

def is_team_member(team_id: str, user_id: str) -> bool:
    """Check if user is a member of the team"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id FROM team_members
                WHERE team_id = ? AND user_id = ? AND is_active = 1
            ''', (team_id, user_id))
            
            return cursor.fetchone() is not None
            
    except Exception as e:
        print(f"Error checking team membership: {e}")
        return False

def log_team_activity(team_id: str, user_id: str, activity_type: str, activity_data: str = ""):
    """Log team activity"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO team_activity (team_id, user_id, activity_type, activity_data)
                VALUES (?, ?, ?, ?)
            ''', (team_id, user_id, activity_type, activity_data))
            
            conn.commit()
            
    except Exception as e:
        print(f"Error logging activity: {e}")

def get_team_activity(team_id: str, limit: int = 20) -> List[Dict]:
    """Get recent team activity"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT ta.activity_type, ta.activity_data, ta.created_at, u.username
                FROM team_activity ta
                JOIN auth_users u ON ta.user_id = u.user_id
                WHERE ta.team_id = ?
                ORDER BY ta.created_at DESC
                LIMIT ?
            ''', (team_id, limit))
            
            activities = []
            for row in cursor.fetchall():
                activities.append({
                    'activity_type': row[0],
                    'activity_data': row[1],
                    'created_at': row[2],
                    'username': row[3]
                })
            
            return activities
            
    except Exception as e:
        print(f"Error getting team activity: {e}")
        return []

if __name__ == "__main__":
    setup_team_database()
    print("✅ Team collaboration system ready!")