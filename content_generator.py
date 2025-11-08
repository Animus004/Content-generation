#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Content Factory: Multi-Niche Generator
Streamlit web application for generating viral content ideas using Gemini AI
"""

# ADD TO THE VERY TOP OF content_generator.py
import streamlit as st 
import json  # Make sure this is imported if not already
import os
from typing import Dict, Any, List

# Initialize session state for copy notifications
if 'copy_status' not in st.session_state:
    st.session_state.copy_status = {}

def add_copy_script():
    """Add JavaScript for clipboard functionality"""
    st.markdown("""
    <script>
    function copyToClipboard(elementId, text) {
        navigator.clipboard.writeText(text).then(function() {
            console.log('Text copied to clipboard');
        }).catch(function(err) {
            console.error('Failed to copy text: ', err);
        });
    }
    </script>
    """, unsafe_allow_html=True)

# Try importing the google-generativeai library with enhanced error handling
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError as e:
    st.error(f"Failed to import google.generativeai: {e}")
    st.error("Please install: pip install google-generativeai")
    GENAI_AVAILABLE = False
    st.stop()
except Exception as e:
    st.error(f"Unexpected error importing Gemini AI: {e}")
    GENAI_AVAILABLE = False
    st.stop()

# Import database manager for content tracking
try:
    from db_manager import (
        setup_database, 
        get_current_day, 
        log_idea, 
        check_for_duplication
    )
    DB_AVAILABLE = True
except ImportError as e:
    st.warning(f"Database manager not available: {e}")
    st.info("Content will be generated without database tracking.")
    DB_AVAILABLE = False

# Import authentication system
try:
    from user_auth import (
        setup_auth_database,
        create_user,
        authenticate_user,
        create_session,
        verify_session,
        get_user_stats,
        log_generation_activity,
        logout_user
    )
    AUTH_AVAILABLE = True
    setup_auth_database()  # Initialize auth database
except ImportError as e:
    st.warning(f"Authentication system not available: {e}")
    AUTH_AVAILABLE = False

# Import team collaboration system
try:
    from team_ui import (
        show_teams_interface,
        show_create_team_modal,
        show_join_team_modal,
        show_team_dashboard,
        add_team_share_button,
        initialize_team_system
    )
    TEAMS_AVAILABLE = True
    initialize_team_system()  # Initialize team system
except ImportError as e:
    st.warning(f"Team collaboration not available: {e}")
    TEAMS_AVAILABLE = False

# Import simple API key management
try:
    from simple_api_manager import (
        ensure_api_key_configured,
        get_configured_api_key,
        show_database_access
    )
    API_MANAGER_AVAILABLE = True
except ImportError as e:
    st.warning(f"API key manager not available: {e}")
    API_MANAGER_AVAILABLE = False

# JSON Schema for structured output - ENHANCED for time slots and detailed Veo 3.1 scripts
JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "niche": {"type": "string", "description": "The content niche (Make Money Online / Personal Finance, AI/Tech Tutorials, Faceless Theme Page)"},
            "time_slot": {"type": "string", "description": "Time interval for posting (Morning, Evening, Night)"},
            "title": {"type": "string", "description": "Catchy title/hook (max 60 characters)"},
            "caption_hook": {"type": "string", "description": "Engaging caption hook (max 150 characters) optimized for the specific time slot"},
            "video_script": {"type": "string", "description": "Extremely detailed 3-shot video description optimized for Google Veo 3.1 with specific camera angles, lighting, and visual elements."},
            "full_audio_script": {"type": "string", "description": "Complete narration text split into 3 parts optimized for Google Text-to-Speech that syncs perfectly with video_script."}
        },
        "required": ["niche", "time_slot", "title", "caption_hook", "video_script", "full_audio_script"]
    }
}

# System instruction for Gemini - ENHANCED for same-day time intervals with detailed video + audio
SYSTEM_INSTRUCTION = """
You are a Top-Tier Viral Content Strategist with expertise in creating engaging, shareable content 
across multiple niches. Your specialty is crafting content that resonates with audiences and 
drives high engagement rates. You understand current trends, audience psychology, and what makes 
content go viral in today's digital landscape.

You excel at creating concise, compelling hooks and titles that capture attention immediately. 
Your video scripts are designed to work seamlessly with Google Veo 3.1 AI video generation,
with extremely detailed shot descriptions, camera angles, and visual elements. Your audio scripts 
provide perfect narration that syncs with the visual elements and work great with Google Text-to-Speech.

CRITICAL REQUIREMENTS:
1. ORIGINALITY: Ensure every title/hook has NEVER been generated before. Prioritize absolute originality.
2. TREND AWARENESS: Ensure content ideas directly follow the latest trends in each respective niche.
3. TIME INTERVALS: Generate 3 ideas per niche for the SAME DAY at different time intervals (Morning, Evening, Night).
4. VEO 3.1 OPTIMIZATION: Create extremely detailed video scripts with specific camera work, lighting, and visual elements.
5. AUDIO SCRIPTING: Create full narration text that perfectly syncs with video timing and works with Google TTS.
6. SYNCHRONIZATION: Ensure video and audio scripts work together seamlessly for complete production.
7. UNIQUENESS: Avoid any repetition or similarity to previously generated content.
8. ENGAGEMENT: Focus on maximum viral potential and audience engagement.
9. QUANTITY: Generate exactly 3 unique ideas per niche for a total of 9 ideas (all for the same day).
"""

def create_enhanced_user_prompt(niche_data: Dict[str, int]) -> str:
    """
    Create an enhanced user prompt for generating 9 unique ideas with detailed video + audio scripts.
    Now generates 3 ideas per niche for the SAME DAY at different time intervals.
    
    Args:
        niche_data: Dictionary mapping niche names to their current continuation days
        
    Returns:
        str: Enhanced prompt for same-day time interval content with detailed Veo 3.1 scripts
    """
    
    # Map database niche names to display names
    niche_mapping = {
        "MMO": "Make Money Online / Personal Finance",
        "AI/Tech": "AI/Tech Tutorials", 
        "Faceless": "Faceless Theme Page"
    }
    
    prompt = """
Generate THREE (3) high-impact, ORIGINAL content ideas for EACH of these three niches, for a total of NINE (9) unique ideas.

IMPORTANT CHANGE: All 3 ideas per niche are for the SAME DAY but different TIME INTERVALS:
- Idea 1: MORNING content (6 AM - 12 PM target audience)
- Idea 2: EVENING content (5 PM - 9 PM target audience)  
- Idea 3: NIGHT content (9 PM - 12 AM target audience)

CRITICAL INSTRUCTIONS:
- Each niche gets 3 ideas for the SAME continuation day, just different posting times
- The 'video_script' field must contain extremely detailed descriptions for Google Veo 3.1
- Include specific camera angles, lighting, movements, and visual elements
- The 'full_audio_script' MUST be split into three parts that sync perfectly with video
- Optimize for different audience mindsets throughout the day
- Ensure the content has NEVER been generated before
- Focus on viral potential and maximum audience engagement at each time slot

"""

    for db_niche, display_name in niche_mapping.items():
        current_day = niche_data.get(db_niche, 0) + 1  # Next day number
        
        if db_niche == "MMO":
            prompt += f"""
## **{display_name}** - Generate 3 Time-Slot Ideas for Day {current_day}

**Morning Content (6 AM - 12 PM)**: Target busy professionals starting their day
**Evening Content (5 PM - 9 PM)**: Target people winding down, planning finances  
**Night Content (9 PM - 12 AM)**: Target late-night researchers and side-hustlers

   - Focus: Quick investment tips and money-making strategies - LATEST TRENDS
   - Target: People at different energy levels throughout the day
   - Time-Specific: Tailor content mood to morning rush, evening planning, or night research
   - Innovation: Use cutting-edge financial trends and time-sensitive opportunities
   
**Veo 3.1 Video Script Requirements for this niche:**
- Shot 1 (8 sec): Detailed camera work - close-ups, wide shots, specific angles and lighting
- Shot 2 (8 sec): Precise visual demonstrations with screen recordings, hand movements, props
- Shot 3 (8 sec): Dynamic conclusion with specific camera movements and visual effects

**Audio Script Requirements for this niche:**
- Shot 1 Audio: Time-appropriate energy level (energetic morning, calm evening, focused night)
- Shot 2 Audio: Clear step-by-step explanation matching the video's visual complexity
- Shot 3 Audio: Strong call-to-action appropriate for the time of day

"""
        elif db_niche == "AI/Tech":
            prompt += f"""
## **{display_name}** - Generate 3 Time-Slot Ideas for Day {current_day}

**Morning Content (6 AM - 12 PM)**: Target tech workers starting their workday
**Evening Content (5 PM - 9 PM)**: Target tech enthusiasts exploring after work
**Night Content (9 PM - 12 AM)**: Target developers and late-night tech learners

   - Focus: Latest AI developments and zero-cost tools - CUTTING EDGE FEATURES
   - Target: Tech audience with different availability and focus levels
   - Time-Specific: Match content complexity to audience attention span by time
   - Innovation: Cover the newest AI capabilities and breakthrough features
   
**Veo 3.1 Video Script Requirements for this niche:**
- Shot 1 (8 sec): Detailed tech setup shots with specific screen angles and interface focus
- Shot 2 (8 sec): Precise demonstration with mouse movements, code snippets, UI navigation
- Shot 3 (8 sec): Results showcase with specific visual transitions and effect highlights

**Audio Script Requirements for this niche:**
- Shot 1 Audio: Tech-appropriate energy matching time (productive morning, exploratory evening, deep-dive night)
- Shot 2 Audio: Technical explanation with precise terminology and step-by-step guidance
- Shot 3 Audio: Encouraging conclusion that motivates immediate experimentation

"""
        elif db_niche == "Faceless":
            prompt += f"""
## **{display_name}** - Generate 3 Time-Slot Ideas for Day {current_day}

**Morning Content (6 AM - 12 PM)**: Target people seeking morning motivation and productivity
**Evening Content (5 PM - 9 PM)**: Target professionals reflecting on their day and goals
**Night Content (9 PM - 12 AM)**: Target people doing late-night self-reflection and planning

   - Focus: Time-appropriate motivational content for productivity and success
   - Target: Working professionals and entrepreneurs at different emotional states
   - Time-Specific: Match motivational tone to daily rhythm and mindset
   - Innovation: Fresh perspective on productivity and success mindset
   
**Veo 3.1 Video Script Requirements for this niche:**
- Shot 1 (8 sec): Cinematic inspirational shots with specific lighting and composition
- Shot 2 (8 sec): Visual metaphors and symbolic imagery with precise camera movements
- Shot 3 (8 sec): Powerful visual conclusion with specific text overlays and transitions

**Audio Script Requirements for this niche:**
- Shot 1 Audio: Inspirational tone matching time energy (uplifting morning, reflective evening, contemplative night)
- Shot 2 Audio: Relatable explanation connecting to time-specific challenges and opportunities
- Shot 3 Audio: Empowering conclusion that motivates action appropriate for the time

"""
    
    prompt += f"""

## OUTPUT REQUIREMENTS:

For each of the 9 ideas (3 per niche, same day, different times), provide:
- **Title**: A catchy title/hook (max 60 characters) - MUST be completely original
- **Caption Hook**: An engaging caption hook (max 150 characters) for the specific time slot
- **Video Script**: An extremely detailed 3-shot video script optimized for Google Veo 3.1
- **Full Audio Script**: Complete narration text that perfectly syncs and works with Google TTS

**Enhanced Video Script Format for Veo 3.1:**
"Shot 1 (8 sec): [Camera angle: close-up/wide/medium], [Lighting: natural/studio/dramatic], [Subject action: specific movements], [Background: detailed environment], [Visual elements: props, graphics, text overlays]
Shot 2 (8 sec): [Camera movement: pan/zoom/static], [Focus: what's in focus/depth of field], [Action sequence: precise step-by-step], [Visual effects: transitions, highlights], [Screen elements: UI, data, demonstrations]  
Shot 3 (8 sec): [Final camera position], [Lighting change if any], [Conclusion action], [Text overlays: specific call-to-action], [Visual finale: how it ends]"

**Audio Script Format for Google TTS:**
"Shot 1 Audio: [8-second narration with natural pauses and emphasis points for TTS]
Shot 2 Audio: [8-second explanation with clear pronunciation guides and pacing]
Shot 3 Audio: [8-second conclusion with strong vocal emphasis and call-to-action tone]"

**TIME SLOT OPTIMIZATION:**
- Morning: High energy, quick tips, productivity focused
- Evening: Moderate pace, detailed explanations, planning oriented  
- Night: Thoughtful tone, in-depth content, reflection based

**SYNCHRONIZATION REQUIREMENT:**
The audio script must perfectly match the timing and visual complexity of the video script. Each audio segment should enhance and complement the corresponding visual shot while being optimized for Google Text-to-Speech natural delivery.

Make sure each piece of content is:
1. Completely original and time-slot appropriate
2. Following current trends in that niche with time-specific angles
3. Optimized for the target audience's mindset at each time of day
4. Designed for maximum viral potential with detailed Veo 3.1 compatibility
5. Includes professional narration optimized for Google TTS conversion

GENERATE EXACTLY 9 IDEAS TOTAL (3 per niche for the same day, different time slots).
"""
    
    return prompt


def initialize_gemini_client():
    """
    Initialize the Gemini client using the API key from various sources.
    
    Returns:
        genai.GenerativeModel: Configured Gemini model instance
        
    Raises:
        ValueError: If no API key is available
        Exception: If there's an error initializing the client
    """
    try:
        # Get API key from the improved API manager or environment
        if API_MANAGER_AVAILABLE:
            api_key = get_configured_api_key()
        else:
            api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            st.error("⚠️ No Gemini API key found.")
            st.info("Please configure your API key using the sidebar or set GEMINI_API_KEY environment variable.")
            if API_MANAGER_AVAILABLE:
                st.info("👈 Use the sidebar to set up your API key for easy access!")
            raise ValueError("No Gemini API key available")
        
        # Validate API key format
        if not api_key.startswith('AIza') or len(api_key) < 35:
            st.error("⚠️ Invalid Gemini API key format.")
            st.info("Please check your API key format. It should start with 'AIza' and be at least 36 characters long.")
            raise ValueError("Invalid API key format")
        
        # Configure the Gemini client with error handling
        try:
            genai.configure(api_key=api_key)
            st.success("🔗 Gemini API configured successfully")
        except Exception as config_error:
            st.error(f"Failed to configure Gemini API: {config_error}")
            raise Exception(f"Error configuring Gemini API: {config_error}")
        
        # Initialize the model with system instruction
        try:
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash-exp",
                system_instruction=SYSTEM_INSTRUCTION
            )
            return model
        except Exception as model_error:
            st.error(f"Failed to initialize Gemini model: {model_error}")
            raise Exception(f"Error initializing Gemini model: {model_error}")
        
    except ValueError as ve:
        st.error(f"Configuration error: {ve}")
        raise ve
    except Exception as e:
        st.error(f"Unexpected error during initialization: {e}")
        raise Exception(f"Error initializing Gemini client: {e}")


def generate_content_ideas(model):
    """
    Generate 9 content ideas (3 per niche) using the Gemini model with database integration.
    Enhanced with comprehensive error handling and validation.
    
    Args:
        model: Configured Gemini model instance
        
    Returns:
        List[Dict[str, Any]]: List of 9 content ideas with video scripts in JSON format
        
    Raises:
        Exception: If there's an error generating content or parsing the response
    """
    progress_bar = st.progress(0)
    status_container = st.container()
    
    try:
        with status_container:
            st.info("🔄 Starting content generation process...")
            progress_bar.progress(10)
        
        # Initialize database if available
        if DB_AVAILABLE:
            try:
                setup_database()
                with status_container:
                    st.info("📊 Database initialized - tracking content progression...")
                progress_bar.progress(20)
            except Exception as db_error:
                st.warning(f"Database setup error: {db_error}")
                st.info("Continuing without database tracking...")
        
        # Get current continuation days for each niche with error handling
        niche_data = {}
        if DB_AVAILABLE:
            try:
                niche_data = {
                    "MMO": get_current_day("MMO"),
                    "AI/Tech": get_current_day("AI/Tech"), 
                    "Faceless": get_current_day("Faceless")
                }
                
                with status_container:
                    st.info(f"📈 Generating 3 ideas per niche: MMO (Days {niche_data['MMO'] + 1}-{niche_data['MMO'] + 3}), AI/Tech (Days {niche_data['AI/Tech'] + 1}-{niche_data['AI/Tech'] + 3}), Faceless (Days {niche_data['Faceless'] + 1}-{niche_data['Faceless'] + 3})")
                progress_bar.progress(30)
                
            except Exception as e:
                st.warning(f"Could not retrieve continuation days: {e}")
                niche_data = {"MMO": 0, "AI/Tech": 0, "Faceless": 0}
        else:
            niche_data = {"MMO": 0, "AI/Tech": 0, "Faceless": 0}
        
        # Create enhanced prompt with continuation day information for 9 ideas
        try:
            enhanced_prompt = create_enhanced_user_prompt(niche_data)
            progress_bar.progress(40)
        except Exception as prompt_error:
            st.error(f"Error creating prompt: {prompt_error}")
            raise Exception(f"Failed to create generation prompt: {prompt_error}")
        
        with status_container:
            st.info("🎬 Generating 9 unique ideas with detailed video scripts for Veo 3 compatibility...")
        progress_bar.progress(50)
        
        # Generate content with structured output - enhanced error handling
        try:
            response = model.generate_content(
                enhanced_prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=JSON_SCHEMA,
                    temperature=0.9,  # High creativity for originality across 9 ideas
                    max_output_tokens=6144  # Increased significantly for 9 detailed video scripts
                )
            )
            progress_bar.progress(70)
            
            # Validate response
            if not response or not response.text:
                raise Exception("Empty response received from Gemini API")
                
        except Exception as api_error:
            error_msg = str(api_error)
            if "quota" in error_msg.lower() or "limit" in error_msg.lower():
                st.error("🚫 API quota exceeded. Please check your Gemini API usage limits.")
                st.info("Try again later or upgrade your API plan.")
            elif "safety" in error_msg.lower():
                st.error("🛡️ Content was blocked by safety filters. Try rephrasing your request.")
            elif "network" in error_msg.lower() or "timeout" in error_msg.lower():
                st.error("🌐 Network error. Please check your internet connection and try again.")
            else:
                st.error(f"🚫 API Error: {error_msg}")
            
            raise Exception(f"Failed to generate content: {api_error}")
        
        # Parse the JSON response with validation
        try:
            content_ideas = json.loads(response.text)
            progress_bar.progress(80)
            
            # Validate response structure
            if not isinstance(content_ideas, list):
                raise ValueError("Response is not a list of ideas")
            
            # Validate each idea has required fields
            for i, idea in enumerate(content_ideas):
                required_fields = ['title', 'niche', 'time_slot', 'caption_hook', 'video_script', 'full_audio_script']
                missing_fields = [field for field in required_fields if field not in idea or not idea[field]]
                
                if missing_fields:
                    st.warning(f"⚠️ Idea {i+1} missing fields: {', '.join(missing_fields)}")
                    
        except json.JSONDecodeError as json_error:
            st.error(f"🚫 Failed to parse AI response as JSON: {json_error}")
            st.code(response.text[:500] + "..." if len(response.text) > 500 else response.text)
            raise Exception(f"Invalid JSON response: {json_error}")
        except Exception as parse_error:
            st.error(f"🚫 Error validating response: {parse_error}")
            raise Exception(f"Response validation failed: {parse_error}")
        
        # Validate we got the expected number of ideas
        if len(content_ideas) != 9:
            st.warning(f"Expected 9 ideas, got {len(content_ideas)}. Proceeding with available ideas.")
        elif len(content_ideas) == 0:
            raise Exception("No content ideas were generated")
        
        progress_bar.progress(90)
        
        # Validate and log ideas to database if available
        if DB_AVAILABLE:
            logged_ideas = []
            duplicate_count = 0
            db_errors = 0
            
            # Track day counters for each niche during this session
            session_counters = {
                "MMO": niche_data.get("MMO", 0),
                "AI/Tech": niche_data.get("AI/Tech", 0),
                "Faceless": niche_data.get("Faceless", 0)
            }
            
            for i, idea in enumerate(content_ideas, 1):
                try:
                    title = idea.get('title', '')
                    niche_display = idea.get('niche', '')
                    
                    # Validate idea content
                    if not title or len(title.strip()) == 0:
                        st.warning(f"⚠️ Idea {i} has empty title, skipping database log")
                        continue
                    
                    # Map display niche back to database niche
                    db_niche = None
                    if "Personal Finance" in niche_display or "Money" in niche_display:
                        db_niche = "MMO"
                    elif "AI" in niche_display or "Tech" in niche_display:
                        db_niche = "AI/Tech"
                    elif "Faceless" in niche_display:
                        db_niche = "Faceless"
                    
                    if db_niche and title:
                        # Check for duplication with error handling
                        try:
                            is_duplicate = check_for_duplication(title)
                            if not is_duplicate:
                                # Increment the session counter for this niche
                                session_counters[db_niche] += 1
                                next_day = session_counters[db_niche]
                                
                                if log_idea(title, db_niche, next_day):
                                    logged_ideas.append(f"{db_niche} Day {next_day}")
                                else:
                                    db_errors += 1
                            else:
                                duplicate_count += 1
                                st.warning(f"⚠️ Potential duplicate detected: {title[:50]}...")
                        except Exception as db_op_error:
                            st.warning(f"Database operation error for idea {i}: {db_op_error}")
                            db_errors += 1
                            
                except Exception as e:
                    st.error(f"Error processing idea {i}: {e}")
                    db_errors += 1
            
            # Report database logging results
            if logged_ideas:
                st.success(f"✅ Successfully logged {len(logged_ideas)} new ideas: {', '.join(logged_ideas)}")
            if duplicate_count > 0:
                st.warning(f"⚠️ {duplicate_count} potential duplicate(s) detected")
            if db_errors > 0:
                st.warning(f"⚠️ {db_errors} database error(s) occurred during logging")
        
        progress_bar.progress(100)
        with status_container:
            st.success(f"🎬 Generated {len(content_ideas)} ideas with detailed video scripts!")
        
        return content_ideas
        
    except Exception as e:
        progress_bar.progress(100)  # Complete the progress bar even on error
        with status_container:
            st.error(f"🚫 Content generation failed: {e}")
        
        # Log the error for debugging
        import traceback
        st.error("Full error details:")
        st.code(traceback.format_exc())
        
        raise e
    try:
        # Initialize database if available
        if DB_AVAILABLE:
            setup_database()
            st.info("📊 Database initialized - tracking content progression...")
        
        # Get current continuation days for each niche
        niche_data = {}
        if DB_AVAILABLE:
            try:
                niche_data = {
                    "MMO": get_current_day("MMO"),
                    "AI/Tech": get_current_day("AI/Tech"), 
                    "Faceless": get_current_day("Faceless")
                }
                
                st.info(f"📈 Generating 3 ideas per niche: MMO (Days {niche_data['MMO'] + 1}-{niche_data['MMO'] + 3}), AI/Tech (Days {niche_data['AI/Tech'] + 1}-{niche_data['AI/Tech'] + 3}), Faceless (Days {niche_data['Faceless'] + 1}-{niche_data['Faceless'] + 3})")
                
            except Exception as e:
                st.warning(f"Could not retrieve continuation days: {e}")
                niche_data = {"MMO": 0, "AI/Tech": 0, "Faceless": 0}
        else:
            niche_data = {"MMO": 0, "AI/Tech": 0, "Faceless": 0}
        
        # Create enhanced prompt with continuation day information for 9 ideas
        enhanced_prompt = create_enhanced_user_prompt(niche_data)
        
        st.info("🎬 Generating 9 unique ideas with detailed video scripts for Veo 3 compatibility...")
        
        # Generate content with structured output - increased limits for 9 ideas
        response = model.generate_content(
            enhanced_prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=JSON_SCHEMA,
                temperature=0.9,  # High creativity for originality across 9 ideas
                max_output_tokens=6144  # Increased significantly for 9 detailed video scripts
            )
        )
        
        # Parse the JSON response
        content_ideas = json.loads(response.text)
        
        # Validate we got exactly 9 ideas
        if len(content_ideas) != 9:
            st.warning(f"Expected 9 ideas, got {len(content_ideas)}. Proceeding with available ideas.")
        
        # Validate and log ideas to database if available
        if DB_AVAILABLE:
            logged_ideas = []
            duplicate_count = 0
            
            # Track day counters for each niche during this session
            session_counters = {
                "MMO": niche_data.get("MMO", 0),
                "AI/Tech": niche_data.get("AI/Tech", 0),
                "Faceless": niche_data.get("Faceless", 0)
            }
            
            for i, idea in enumerate(content_ideas, 1):
                try:
                    title = idea.get('title', '')
                    niche_display = idea.get('niche', '')
                    
                    # Map display niche back to database niche
                    db_niche = None
                    if "Personal Finance" in niche_display or "Money" in niche_display:
                        db_niche = "MMO"
                    elif "AI" in niche_display or "Tech" in niche_display:
                        db_niche = "AI/Tech"
                    elif "Faceless" in niche_display:
                        db_niche = "Faceless"
                    
                    if db_niche and title:
                        # Check for duplication
                        if not check_for_duplication(title):
                            # Increment the session counter for this niche
                            session_counters[db_niche] += 1
                            next_day = session_counters[db_niche]
                            
                            if log_idea(title, db_niche, next_day):
                                logged_ideas.append(f"{db_niche} Day {next_day}")
                        else:
                            duplicate_count += 1
                            st.warning(f"⚠️ Potential duplicate detected: {title[:50]}...")
                            
                except Exception as e:
                    st.error(f"Error processing idea {i}: {e}")
            
            if logged_ideas:
                st.success(f"✅ Successfully logged {len(logged_ideas)} new ideas: {', '.join(logged_ideas)}")
            if duplicate_count > 0:
                st.warning(f"⚠️ {duplicate_count} potential duplicate(s) detected")
        
        st.success(f"🎬 Generated {len(content_ideas)} ideas with detailed video scripts!")
        return content_ideas
        
    except json.JSONDecodeError as je:
        error_msg = f"Error parsing JSON response: {je}"
        st.error(error_msg)
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"Error generating content: {e}"
        st.error(error_msg)
        raise Exception(error_msg)


def generate_viral_ideas():
    """
    Main function to generate viral content ideas with database integration.
    
    Returns:
        str: JSON string of generated content ideas, or None if error
    """
    try:
        # Initialize Gemini client
        model = initialize_gemini_client()
        
        # Generate content ideas with database integration
        content_ideas = generate_content_ideas(model)
        
        # Return JSON string
        return json.dumps(content_ideas, indent=4, ensure_ascii=False)
        
    except Exception as e:
        st.error(f"🚨 Generation Error: {e}")
        
        # Provide helpful troubleshooting information
        if "API" in str(e).upper():
            st.error("🔑 Check your Gemini API key and internet connection")
        elif "DATABASE" in str(e).upper():
            st.error("🗄️ Database error - content generated but not tracked")
        elif "JSON" in str(e).upper():
            st.error("📄 Response parsing error - try regenerating content")
        
        return None


# ADD THIS MAIN FUNCTION TO THE BOTTOM OF content_generator.py
def show_login_page():
    """Display login/signup interface"""
    st.title("🔐 AI Content Factory - Login")
    st.markdown("### Welcome to the Multi-Niche Video Generator")
    
    # Initialize session state for auth
    if 'auth_mode' not in st.session_state:
        st.session_state.auth_mode = 'login'
    
    # Toggle between login and signup
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔑 Login", type="primary" if st.session_state.auth_mode == 'login' else "secondary"):
            st.session_state.auth_mode = 'login'
    with col2:
        if st.button("📝 Sign Up", type="primary" if st.session_state.auth_mode == 'signup' else "secondary"):
            st.session_state.auth_mode = 'signup'
    
    st.markdown("---")
    
    if st.session_state.auth_mode == 'login':
        show_login_form()
    else:
        show_signup_form()

def show_login_form():
    """Login form"""
    st.subheader("🔑 Login to Your Account")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", type="primary")
        
        if submit:
            if not username or not password:
                st.error("Please enter both username and password")
                return
            
            success, message, user_id = authenticate_user(username, password)
            if success:
                session_id = create_session(user_id)
                st.session_state.session_id = session_id
                st.session_state.user_id = user_id
                st.session_state.username = username
                st.session_state.authenticated = True
                st.success(message)
                st.rerun()
            else:
                st.error(message)

def show_signup_form():
    """Signup form"""
    st.subheader("📝 Create New Account")
    
    with st.form("signup_form"):
        username = st.text_input("Choose Username (min 3 characters)")
        email = st.text_input("Email Address")
        password = st.text_input("Password (min 6 characters)", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Create Account", type="primary")
        
        if submit:
            if not all([username, email, password, confirm_password]):
                st.error("Please fill in all fields")
                return
            
            if password != confirm_password:
                st.error("Passwords do not match")
                return
            
            success, message, user_id = create_user(username, email, password)
            if success:
                st.success(message)
                st.info("You can now login with your new account!")
                st.session_state.auth_mode = 'login'
                st.rerun()
            else:
                st.error(message)

def show_user_dashboard():
    """Show user profile and stats"""
    if not AUTH_AVAILABLE:
        return
    
    user_stats = get_user_stats(st.session_state.user_id)
    
    with st.sidebar:
        st.markdown("---")
        st.subheader(f"👤 {st.session_state.username}")
        st.write(f"**Email:** {user_stats['email']}")
        st.write(f"**Member Since:** {user_stats['member_since'][:10]}")
        st.write(f"**Total Ideas Generated:** {user_stats['total_ideas']}")
        st.write(f"**Generation Sessions:** {user_stats['total_sessions']}")
        st.write(f"**Recent Activity (7d):** {user_stats['recent_ideas']} ideas")
        
        # Add team interface
        if TEAMS_AVAILABLE:
            show_teams_interface()
            if st.sidebar.button("🏢 Team Dashboard", key="teams_dashboard"):
                st.session_state.show_teams_page = True
                st.rerun()
        
        if st.button("🚪 Logout"):
            logout_user(st.session_state.session_id)
            for key in ['authenticated', 'session_id', 'user_id', 'username']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

def check_authentication():
    """Check if user is authenticated"""
    if not AUTH_AVAILABLE:
        return True  # Skip auth if not available
    
    # Check if user has valid session
    if 'authenticated' in st.session_state and st.session_state.authenticated:
        if 'session_id' in st.session_state:
            valid, user_id, username = verify_session(st.session_state.session_id)
            if valid:
                st.session_state.user_id = user_id
                st.session_state.username = username
                return True
            else:
                # Session expired
                for key in ['authenticated', 'session_id', 'user_id', 'username']:
                    if key in st.session_state:
                        del st.session_state[key]
    
    return False

def main_app():
    st.set_page_config(layout="wide", page_title="AI Content Factory", page_icon="💡")
    
    # Show API Key setup in sidebar (must be done first)
    api_key_configured = False
    if API_MANAGER_AVAILABLE:
        api_key_configured = ensure_api_key_configured()
        # Show database access option
        show_database_access()
    
    # Show team modals if needed
    if TEAMS_AVAILABLE:
        show_create_team_modal()
        show_join_team_modal()
    
    # Check if user wants to view team dashboard
    if st.session_state.get('show_teams_page', False):
        show_team_dashboard()
        if st.button("🔙 Back to Content Generator"):
            st.session_state.show_teams_page = False
            st.rerun()
        return
    
    st.title("💡 AI Content Factory: Multi-Niche Video Generator")
    st.subheader("Generate 9 Unique Video Ideas with Detailed Scripts using Gemini AI")
    
    # Show API key requirement message if not configured
    if not api_key_configured and not os.getenv('GEMINI_API_KEY'):
        st.warning("⚠️ Please configure your Gemini API key in the sidebar to start generating content!")
        st.info("👈 Check the sidebar for API key setup instructions.")
        return
    
    # Sidebar for information
    with st.sidebar:
        st.header("📋 About")
        st.write("Generate viral content ideas for:")
        st.write("• 💰 Personal Finance")
        st.write("• 🤖 AI/Tech Tutorials")
        st.write("• 🎯 Faceless Theme Pages")
        
        # Database Status
        st.header("🗄️ Content Tracking")
        if DB_AVAILABLE:
            try:
                # Initialize database to ensure it exists
                setup_database()
                
                # Get current progression
                mmo_day = get_current_day("MMO")
                tech_day = get_current_day("AI/Tech") 
                faceless_day = get_current_day("Faceless")
                
                st.success("✅ Database Connected")
                st.write("**Current Series Progress:**")
                st.write(f"💰 Personal Finance: Day {mmo_day + 1}")
                st.write(f"🤖 AI/Tech: Day {tech_day + 1}")
                st.write(f"🎯 Faceless: Day {faceless_day + 1}")
                
                # Show total ideas generated
                total_ideas = mmo_day + tech_day + faceless_day
                if total_ideas > 0:
                    st.info(f"📊 Total Ideas Generated: {total_ideas}")
                    
            except Exception as e:
                st.error("❌ Database Error")
                st.caption(f"Error: {str(e)[:50]}...")
        else:
            st.warning("⚠️ Database Unavailable")
            st.caption("Content will be generated without tracking")
        
        # API Key Guide (only show if API manager not available)
        if not API_MANAGER_AVAILABLE:
            st.header("🔧 API Key Setup")
            
            with st.expander("🔑 How to Get Your Free API Key", expanded=False):
                st.write("**Step 1:** Visit Google AI Studio")
                st.write("👉 [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)")
                
                st.write("**Step 2:** Sign in with Google Account")
                st.write("• Use your existing Google account")
                st.write("• Or create a new one (free)")
                
                st.write("**Step 3:** Create API Key")
                st.write("• Click 'Create API Key'")
                st.write("• Choose 'Create API key in new project'")
                st.write("• Copy the generated key")
                
                st.write("**Step 4:** Paste Key Below")
                st.write("• The key starts with 'AIza...'")
                st.write("• Keep it private and secure")
            
            st.info("💡 **Tip:** The Gemini API has a generous free tier - perfect for content generation!")
        
        # Privacy Notice
        with st.expander("🔒 Privacy & Security Notice", expanded=False):
            st.write("**🛡️ Your API Key is SAFE:**")
            st.write("• ✅ NOT stored on any server")
            st.write("• ✅ NOT logged or recorded")
            st.write("• ✅ Only used for this session")
            st.write("• ✅ Automatically cleared when you close the app")
            
            st.write("**🔐 Technical Details:**")
            st.write("• Key is stored in temporary session memory only")
            st.write("• Direct communication: Your Browser → Google AI")
            st.write("• No third-party servers involved")
            st.write("• Application runs locally on your machine")
            
            st.success("🔒 **100% Privacy Guaranteed** - We never see or store your API key!")
        
        # API Key input
        api_key_input = st.text_input(
            "🔑 Enter Your Gemini API Key", 
            value="",
            type="password",
            placeholder="AIzaSy...",
            help="Paste your API key from Google AI Studio here"
        )
        
        if api_key_input:
            # Validate API key format
            if api_key_input.startswith('AIza') and len(api_key_input) > 35:
                # Set the environment variable for this session
                os.environ['GEMINI_API_KEY'] = api_key_input
                st.success("✅ Valid API Key Set")
                st.info("🚀 Ready to generate content!")
            else:
                st.error("❌ Invalid API key format")
                st.write("Expected format: AIzaSy...")
        else:
            st.warning("⚠️ API Key Required")
            st.write("👆 Get your free key from Google AI Studio")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write("Click the button below to generate **9 unique content ideas** (3 per niche) with:")
        st.write("• 🔄 **Continuation tracking** - Builds on previous content series")
        st.write("• 🚫 **Duplicate prevention** - Ensures complete originality") 
        st.write("• 📈 **Trend integration** - Latest niche developments")
        st.write("• 🎬 **Video scripts** - 3-shot descriptions for AI video generation (Veo 3)")
        st.write("• 🗄️ **Auto-logging** - Tracks your content progression")
        
        # Check if API key is available before showing the button
        if not os.getenv('GEMINI_API_KEY'):
            st.warning("⚠️ Please enter your Gemini API key in the sidebar first.")
            st.stop()
        
        # The button to trigger the API call
        if st.button("🚀 Generate 9 Viral Ideas (Same Day - Morning/Evening/Night)", type="primary", use_container_width=True):
            with st.spinner("🎬 Connecting to Gemini AI and generating 9 time-slot optimized ideas with detailed Veo 3.1 + Audio scripts..."):
                json_output = generate_viral_ideas()  # Calls enhanced logic with 9 ideas

                if json_output:
                    st.success("✅ 9 Video Ideas Generated Successfully!")
                    
                    # Parse and display the content ideas in a more user-friendly way
                    try:
                        ideas = json.loads(json_output)
                        
                        # Log generation activity for authenticated users
                        if AUTH_AVAILABLE and 'user_id' in st.session_state:
                            niches_used = ", ".join(set([idea['niche'] for idea in ideas]))
                            session_id = st.session_state.get('session_id', '')
                            log_generation_activity(st.session_state.user_id, len(ideas), niches_used, session_id)
                        
                        # Group ideas by niche for better organization
                        niches = {"Make Money Online / Personal Finance": [], "AI/Tech Tutorials": [], "Faceless Theme Page": []}
                        
                        for idea in ideas:
                            niche = idea['niche']
                            if "Personal Finance" in niche or "Money" in niche:
                                niches["Make Money Online / Personal Finance"].append(idea)
                            elif "AI" in niche or "Tech" in niche:
                                niches["AI/Tech Tutorials"].append(idea)
                            elif "Faceless" in niche:
                                niches["Faceless Theme Page"].append(idea)
                        
                        # Display ideas grouped by niche
                        for niche_name, niche_ideas in niches.items():
                            if niche_ideas:
                                st.subheader(f"🎯 {niche_name} ({len(niche_ideas)} Ideas)")
                                
                                for i, idea in enumerate(niche_ideas, 1):
                                    with st.expander(f"💡 Idea {i}: {idea['title']}", expanded=True):
                                        st.write(f"**🎯 Title:** {idea['title']}")
                                        st.write(f"**📝 Caption Hook:** {idea['caption_hook']}")
                                        st.write(f"**� Video Script (3 Shots):**")
                                        
                                        # Format video script for better readability
                                        video_script = idea.get('video_script', '')
                                        if video_script:
                                            # Split into individual shots if properly formatted
                                            shots = video_script.split('Shot')
                                            if len(shots) > 1:
                                                for j, shot in enumerate(shots[1:], 1):
                                                    shot_content = shot.strip()
                                                    if shot_content:
                                                        st.write(f"  **Shot {j}:** {shot_content}")
                                            else:
                                                # Display as single block if not formatted as shots
                                                st.write(video_script)
                                        
                                        # Display Audio Script (ADDED MISSING FEATURE!)
                                        audio_script = idea.get('full_audio_script', '')
                                        if audio_script:
                                            st.write(f"**🎙️ Audio Script (Google TTS Ready):**")
                                            # Split audio script into parts if formatted
                                            if 'Part 1:' in audio_script or 'Audio 1:' in audio_script:
                                                parts = audio_script.replace('Part 1:', '**Part 1:**').replace('Part 2:', '**Part 2:**').replace('Part 3:', '**Part 3:**')
                                                parts = parts.replace('Audio 1:', '**Audio 1:**').replace('Audio 2:', '**Audio 2:**').replace('Audio 3:', '**Audio 3:**')
                                                st.markdown(parts)
                                            else:
                                                st.write(audio_script)
                                        else:
                                            st.write("**🎙️ Audio Script:** Not available in this generation")
                                        
                                        # Show database status for this idea
                                        if DB_AVAILABLE:
                                            niche_display = idea['niche']
                                            if "Personal Finance" in niche_display or "Money" in niche_display:
                                                db_niche = "MMO"
                                            elif "AI" in niche_display or "Tech" in niche_display:
                                                db_niche = "AI/Tech"
                                            elif "Faceless" in niche_display:
                                                db_niche = "Faceless"
                                            else:
                                                db_niche = None
                                            
                                            if db_niche:
                                                try:
                                                    current_day = get_current_day(db_niche)
                                                    st.caption(f"🗄️ Logged as {db_niche} Day {current_day}")
                                                except:
                                                    st.caption("🗄️ Database tracking active")
                                        
                                        # Add copy buttons for each element
                                        col_a, col_b, col_c, col_d = st.columns(4)
                                        unique_key = f"{niche_name}_{i}"
                                        with col_a:
                                            if st.button(f"📋 Copy Title", key=f"title_{unique_key}"):
                                                st.write("Title copied to clipboard!")
                                        with col_b:
                                            if st.button(f"📋 Copy Caption", key=f"caption_{unique_key}"):
                                                st.write("Caption copied to clipboard!")
                                        with col_c:
                                            if st.button(f"📋 Copy Video Script", key=f"script_{unique_key}"):
                                                st.write("Video script copied!")
                                        with col_d:
                                            if st.button(f"📋 Copy Audio Script", key=f"audio_{unique_key}"):
                                                st.write("Audio script copied!")
                        
                        # Show raw JSON in an expander
                        with st.expander("🔍 View Raw JSON Output (All 9 Ideas)"):
                            st.json(json.loads(json_output))
                        
                        # Database summary for all 9 ideas
                        if DB_AVAILABLE:
                            with st.expander("📊 Content Progression Summary"):
                                try:
                                    mmo_day = get_current_day("MMO")
                                    tech_day = get_current_day("AI/Tech")
                                    faceless_day = get_current_day("Faceless")
                                    total = mmo_day + tech_day + faceless_day
                                    
                                    col_db1, col_db2, col_db3 = st.columns(3)
                                    with col_db1:
                                        st.metric("💰 Personal Finance", f"Day {mmo_day}")
                                    with col_db2:
                                        st.metric("🤖 AI/Tech", f"Day {tech_day}")
                                    with col_db3:
                                        st.metric("🎯 Faceless", f"Day {faceless_day}")
                                    
                                    st.write(f"**Total Video Ideas Generated:** {total} ideas across all niches")
                                    st.write(f"**This Session:** Added {len(ideas)} new video ideas")
                                except Exception as e:
                                    st.error(f"Error retrieving progression data: {e}")
                        
                        # Team sharing functionality
                        if TEAMS_AVAILABLE and AUTH_AVAILABLE and st.session_state.get('authenticated', False):
                            niches_used = ", ".join(set([idea['niche'] for idea in ideas]))
                            add_team_share_button(json_output, len(ideas), niches_used)
                            
                    except json.JSONDecodeError:
                        st.error("Error parsing generated content")
                        st.text(json_output)
                else:
                    st.error("❌ Error: Could not generate video ideas. Check your API Key and try again.")
                    
                    # Show troubleshooting tips
                    with st.expander("🔧 Troubleshooting Tips"):
                        st.write("**Common Issues:**")
                        st.write("• **API Key**: Ensure it starts with 'AIza' and is complete")
                        st.write("• **Internet**: Check your internet connection")
                        st.write("• **Quota**: Verify your Gemini API usage hasn't exceeded limits")
                        st.write("• **Content Size**: 9 video scripts require more processing time")
                        st.write("• **Database**: Database errors won't prevent content generation")
    
    with col2:
        st.write("### 🎯 Target Niches")
        
        st.write("**💰 Personal Finance**")
        st.caption("Quick investment tips for beginners")
        
        st.write("**🤖 AI/Tech Tutorials**")
        st.caption("Zero-cost Gemini features")
        
        st.write("**🎯 Faceless Theme Pages**")
        st.caption("Daily motivational content")
        
        st.write("### 📊 Output Format")
        st.caption("**Per Idea (9 total):**")
        st.caption("• Title (≤60 chars)")
        st.caption("• Caption Hook (≤150 chars)")
        st.caption("• Video Script (3 shots, 8 sec each)")
        
        st.write("### 🎬 Video Script Format")
        st.caption("**3-Shot Structure:**")
        st.caption("• Shot 1: Hook/Opening (8 sec)")
        st.caption("• Shot 2: Main Content (8 sec)")  
        st.caption("• Shot 3: Conclusion/CTA (8 sec)")
        st.caption("**Optimized for:** Veo 3, Runway, etc.")
    
    # Footer with privacy and security information
    st.markdown("---")
    col_footer1, col_footer2, col_footer3 = st.columns(3)
    
    with col_footer1:
        st.write("**🔒 Privacy Guaranteed**")
        st.caption("Your API key is never stored, logged, or transmitted to any third-party servers.")
    
    with col_footer2:
        st.write("**🚀 Powered by Google Gemini**")
        st.caption("Using Google's latest AI technology for content generation.")
    
    with col_footer3:
        st.write("**💡 Open Source**")
        st.caption("This tool runs locally on your machine for maximum security.")
    
    # Technical details in small text
    st.markdown(
        """
        <div style='text-align: center; color: #666; font-size: 12px; margin-top: 20px;'>
        🔐 <strong>Security Notice:</strong> This application processes your API key in temporary memory only. 
        No data is stored, cached, or transmitted to external servers beyond Google's official Gemini API. 
        Your API key is automatically cleared when the session ends.
        <br><br>
        📝 <strong>Data Flow:</strong> Your Browser → Local App → Google Gemini API → Results Back to You
        <br>
        🛡️ <strong>Zero Data Retention:</strong> We cannot access, view, or store your API key or generated content.
        </div>
        """, 
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    # Main application with authentication
    if AUTH_AVAILABLE and not check_authentication():
        show_login_page()
    else:
        if AUTH_AVAILABLE and check_authentication():
            show_user_dashboard()  # Show user stats in sidebar
        main_app()