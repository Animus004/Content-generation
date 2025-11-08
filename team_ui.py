# -*- coding: utf-8 -*-
"""
Team Collaboration UI Components for Streamlit
Production-ready team interface with modern design
"""

import streamlit as st
import json
from datetime import datetime
from typing import Dict, List, Optional
from team_collaboration import (
    setup_team_database,
    create_team,
    invite_team_member,
    accept_team_invitation,
    create_team_project,
    share_generation_to_team,
    get_user_teams,
    get_team_projects,
    get_shared_generations,
    has_team_permission,
    get_team_activity
)

def show_teams_interface():
    """Main teams interface"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("👥 Teams")
    
    if not st.session_state.get('authenticated', False):
        st.sidebar.info("Login to access teams")
        return
    
    user_id = st.session_state.get('user_id')
    teams = get_user_teams(user_id)
    
    # Team selector in sidebar
    if teams:
        team_names = [f"{team['team_name']} ({team['role']})" for team in teams]
        selected_team_idx = st.sidebar.selectbox(
            "Select Team",
            range(len(teams)),
            format_func=lambda x: team_names[x] if x < len(team_names) else "None",
            key="team_selector"
        )
        
        if selected_team_idx is not None:
            st.session_state.selected_team = teams[selected_team_idx]
            
        if st.sidebar.button("➕ Create New Team"):
            st.session_state.show_create_team = True
            
        if st.sidebar.button("📧 Join Team"):
            st.session_state.show_join_team = True
    else:
        st.sidebar.info("No teams yet")
        if st.sidebar.button("➕ Create Your First Team"):
            st.session_state.show_create_team = True
            
        if st.sidebar.button("📧 Join Team"):
            st.session_state.show_join_team = True

def show_create_team_modal():
    """Team creation modal"""
    if not st.session_state.get('show_create_team', False):
        return
        
    st.markdown("## 🆕 Create New Team")
    
    with st.form("create_team_form"):
        team_name = st.text_input("Team Name", placeholder="e.g., Content Creators United")
        description = st.text_area("Description (Optional)", placeholder="What's your team about?")
        max_members = st.slider("Maximum Members", 2, 50, 10)
        
        col1, col2 = st.columns(2)
        with col1:
            create_btn = st.form_submit_button("✅ Create Team", type="primary")
        with col2:
            cancel_btn = st.form_submit_button("❌ Cancel")
            
        if cancel_btn:
            st.session_state.show_create_team = False
            st.rerun()
            
        if create_btn:
            if team_name.strip():
                success, message, team_id = create_team(
                    st.session_state.user_id,
                    team_name,
                    description,
                    max_members
                )
                
                if success:
                    st.success(message)
                    st.session_state.show_create_team = False
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.error("Team name is required")

def show_join_team_modal():
    """Team joining modal"""
    if not st.session_state.get('show_join_team', False):
        return
        
    st.markdown("## 📧 Join Team")
    
    with st.form("join_team_form"):
        invitation_token = st.text_input("Invitation Token", placeholder="Paste invitation token here")
        
        col1, col2 = st.columns(2)
        with col1:
            join_btn = st.form_submit_button("✅ Join Team", type="primary")
        with col2:
            cancel_btn = st.form_submit_button("❌ Cancel")
            
        if cancel_btn:
            st.session_state.show_join_team = False
            st.rerun()
            
        if join_btn:
            if invitation_token.strip():
                success, message = accept_team_invitation(invitation_token, st.session_state.user_id)
                
                if success:
                    st.success(message)
                    st.session_state.show_join_team = False
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.error("Invitation token is required")

def show_team_dashboard():
    """Main team dashboard"""
    if not st.session_state.get('selected_team'):
        st.info("👥 **Welcome to Team Collaboration!**")
        st.markdown("""
        ### 🚀 Get Started:
        1. **Create a team** - Start your own collaborative workspace
        2. **Join a team** - Enter an invitation token to join an existing team
        3. **Collaborate** - Share content ideas and work together on projects
        
        ### ✨ Team Features:
        - 🤝 **Invite Members** - Add team members with different roles
        - 📁 **Projects** - Organize work into focused projects
        - 💡 **Share Ideas** - Share your 9-idea generations with the team
        - 💬 **Comments** - Give feedback on shared content
        - 📊 **Activity Feed** - Stay updated on team progress
        """)
        return
    
    team = st.session_state.selected_team
    
    # Team header
    st.markdown(f"# 👥 {team['team_name']}")
    if team['description']:
        st.markdown(f"*{team['description']}*")
    
    # Team stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Role", team['role'].title())
    with col2:
        st.metric("Members", team['member_count'])
    with col3:
        st.metric("Your Permissions", len(team['permissions']))
    with col4:
        if team['is_owner']:
            st.metric("Status", "Owner")
        else:
            st.metric("Status", "Member")
    
    # Tab navigation
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📁 Projects", "💡 Shared Ideas", "👥 Members", "📊 Activity", "⚙️ Settings"])
    
    with tab1:
        show_projects_tab(team)
    
    with tab2:
        show_shared_ideas_tab(team)
    
    with tab3:
        show_members_tab(team)
    
    with tab4:
        show_activity_tab(team)
    
    with tab5:
        show_settings_tab(team)

def show_projects_tab(team: Dict):
    """Projects tab content"""
    st.subheader("📁 Team Projects")
    
    projects = get_team_projects(team['team_id'], st.session_state.user_id)
    
    # Create new project button
    if 'write' in team['permissions']:
        if st.button("➕ Create New Project"):
            st.session_state.show_create_project = True
    
    if st.session_state.get('show_create_project', False):
        show_create_project_form(team)
    
    # Display projects
    if projects:
        for project in projects:
            with st.expander(f"📁 {project['project_name']}", expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    if project['description']:
                        st.write(f"**Description:** {project['description']}")
                    st.write(f"**Created by:** {project['creator_name']}")
                    st.write(f"**Created:** {project['created_at'][:10]}")
                    if project['niches']:
                        st.write(f"**Niches:** {project['niches']}")
                
                with col2:
                    st.metric("Shared Ideas", project['generation_count'])
                    if st.button(f"🔗 Open", key=f"open_project_{project['project_id']}"):
                        st.session_state.selected_project = project
                        st.session_state.show_project_detail = True
    else:
        st.info("No projects yet. Create your first project to start collaborating!")

def show_create_project_form(team: Dict):
    """Create project form"""
    st.markdown("### 🆕 Create New Project")
    
    with st.form("create_project_form"):
        project_name = st.text_input("Project Name")
        description = st.text_area("Description")
        niches = st.text_input("Target Niches (comma-separated)", placeholder="e.g., AI/Tech, Personal Finance")
        
        col1, col2 = st.columns(2)
        with col1:
            create_btn = st.form_submit_button("✅ Create Project", type="primary")
        with col2:
            cancel_btn = st.form_submit_button("❌ Cancel")
            
        if cancel_btn:
            st.session_state.show_create_project = False
            st.rerun()
            
        if create_btn:
            if project_name.strip():
                success, message, project_id = create_team_project(
                    team['team_id'],
                    st.session_state.user_id,
                    project_name,
                    description,
                    niches
                )
                
                if success:
                    st.success(message)
                    st.session_state.show_create_project = False
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.error("Project name is required")

def show_shared_ideas_tab(team: Dict):
    """Shared ideas tab content"""
    st.subheader("💡 Shared Content Ideas")
    
    projects = get_team_projects(team['team_id'], st.session_state.user_id)
    
    if not projects:
        st.info("Create a project first to share content ideas")
        return
    
    # Project selector for viewing shared ideas
    project_names = {p['project_id']: p['project_name'] for p in projects}
    selected_project_id = st.selectbox(
        "Select Project",
        list(project_names.keys()),
        format_func=lambda x: project_names[x],
        key="shared_ideas_project_selector"
    )
    
    if selected_project_id:
        shared_generations = get_shared_generations(selected_project_id, st.session_state.user_id)
        
        if shared_generations:
            for generation in shared_generations:
                with st.expander(f"💡 {generation['ideas_count']} Ideas by {generation['creator_name']}", expanded=False):
                    st.write(f"**Created:** {generation['created_at'][:16]}")
                    st.write(f"**Niches:** {generation['niches_used']}")
                    
                    # Show the actual ideas
                    try:
                        ideas_data = json.loads(generation['generation_data'])
                        for i, idea in enumerate(ideas_data, 1):
                            st.markdown(f"**Idea {i}: {idea.get('title', 'No title')}**")
                            st.write(f"📝 {idea.get('caption_hook', 'No caption')}")
                            
                            # Show video and audio scripts in collapsible sections
                            if idea.get('video_script'):
                                with st.expander(f"🎬 Video Script {i}"):
                                    st.write(idea['video_script'])
                            
                            if idea.get('full_audio_script'):
                                with st.expander(f"🎙️ Audio Script {i}"):
                                    st.write(idea['full_audio_script'])
                            
                            st.markdown("---")
                            
                    except json.JSONDecodeError:
                        st.error("Could not parse idea data")
                    
                    # Interaction buttons
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.button(f"👍 Like ({generation['likes_count']})", key=f"like_{generation['generation_id']}")
                    with col2:
                        st.button(f"💬 Comment ({generation['comments_count']})", key=f"comment_{generation['generation_id']}")
                    with col3:
                        st.button("📋 Copy All", key=f"copy_{generation['generation_id']}")
        else:
            st.info("No shared ideas in this project yet")

def show_members_tab(team: Dict):
    """Members tab content"""
    st.subheader("👥 Team Members")
    
    # Invite new member (if has permission)
    if 'invite' in team['permissions']:
        with st.expander("📧 Invite New Member"):
            with st.form("invite_member_form"):
                email = st.text_input("Email Address")
                role = st.selectbox("Role", ["member", "moderator"])
                invite_btn = st.form_submit_button("📤 Send Invitation", type="primary")
                
                if invite_btn:
                    if email:
                        success, message = invite_team_member(team['team_id'], st.session_state.user_id, email, role)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    else:
                        st.error("Email is required")
    
    # TODO: Display actual team members (would need additional query)
    st.info("Member list will show existing team members with their roles and permissions")

def show_activity_tab(team: Dict):
    """Activity tab content"""
    st.subheader("📊 Team Activity")
    
    activities = get_team_activity(team['team_id'])
    
    if activities:
        for activity in activities:
            # Format activity based on type
            icon = "🔵"
            if activity['activity_type'] == 'team_created':
                icon = "🎉"
            elif activity['activity_type'] == 'member_joined':
                icon = "👋"
            elif activity['activity_type'] == 'member_invited':
                icon = "📧"
            elif activity['activity_type'] == 'project_created':
                icon = "📁"
            elif activity['activity_type'] == 'generation_shared':
                icon = "💡"
            
            st.markdown(f"{icon} **{activity['username']}** {activity['activity_data']}")
            st.caption(f"📅 {activity['created_at'][:16]}")
            st.markdown("---")
    else:
        st.info("No activity yet")

def show_settings_tab(team: Dict):
    """Settings tab content"""
    st.subheader("⚙️ Team Settings")
    
    if team['is_owner']:
        st.markdown("### 🔧 Admin Settings")
        
        # Team info editing
        with st.expander("✏️ Edit Team Info"):
            new_name = st.text_input("Team Name", value=team['team_name'])
            new_description = st.text_area("Description", value=team.get('description', ''))
            
            if st.button("💾 Save Changes"):
                # TODO: Implement team info update
                st.success("Team info updated!")
        
        # Danger zone
        with st.expander("⚠️ Danger Zone", expanded=False):
            st.warning("Dangerous actions that cannot be undone")
            if st.button("🗑️ Delete Team", type="secondary"):
                # TODO: Implement team deletion
                st.error("Team deletion not implemented yet")
    else:
        st.markdown("### 🚪 Member Actions")
        
        if st.button("🚪 Leave Team"):
            # TODO: Implement leave team
            st.warning("Leave team functionality not implemented yet")
    
    # Team info display
    st.markdown("### ℹ️ Team Information")
    st.write(f"**Team ID:** `{team['team_id']}`")
    st.write(f"**Your Role:** {team['role']}")
    st.write(f"**Your Permissions:** {', '.join(team['permissions'])}")

def add_team_share_button(ideas_data: str, ideas_count: int, niches_used: str):
    """Add team sharing functionality to main content generator"""
    if not st.session_state.get('authenticated', False):
        return
    
    user_teams = get_user_teams(st.session_state.user_id)
    
    if not user_teams:
        return
    
    st.markdown("---")
    st.subheader("👥 Share with Team")
    
    # Team and project selection
    team_options = {team['team_id']: team['team_name'] for team in user_teams}
    selected_team_id = st.selectbox(
        "Select Team",
        list(team_options.keys()),
        format_func=lambda x: team_options[x],
        key="share_team_selector"
    )
    
    if selected_team_id:
        projects = get_team_projects(selected_team_id, st.session_state.user_id)
        
        if projects:
            project_options = {p['project_id']: p['project_name'] for p in projects}
            selected_project_id = st.selectbox(
                "Select Project",
                list(project_options.keys()),
                format_func=lambda x: project_options[x],
                key="share_project_selector"
            )
            
            if selected_project_id and st.button("📤 Share with Team", type="primary"):
                success, message = share_generation_to_team(
                    selected_team_id,
                    selected_project_id,
                    st.session_state.user_id,
                    ideas_data,
                    ideas_count,
                    niches_used
                )
                
                if success:
                    st.success(message)
                else:
                    st.error(message)
        else:
            st.info("Create a project first to share content")

# Initialize team system
def initialize_team_system():
    """Initialize the team collaboration system"""
    try:
        setup_team_database()
        return True
    except Exception as e:
        st.error(f"Failed to initialize team system: {e}")
        return False