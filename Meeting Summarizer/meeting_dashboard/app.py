from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.utils import secure_filename
import os
import asyncio
from datetime import datetime

from config import config
from extensions import init_extensions
from models import db, User, Meeting, ActionItem
from agents.groq_client import GroqClient
from agents.summarizer_agent import SummarizerAgent
from agents.action_agent import ActionAgent
from utils.file_utils import allowed_file, parse_transcript_file, transcribe_audio_faster_whisper
from utils.viz_utils import generate_action_timeline_data
from utils.google_calendar import create_google_meet_event
from utils.zoom_meeting import process_zoom_meeting, extract_meeting_info_from_url

def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    init_extensions(app)
    # Ensure tables exist (for dev). For schema changes, delete the SQLite file once to recreate.
    with app.app_context():
        db.create_all()
    
    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize Groq client and agents
    groq_client = GroqClient(app.config['GROQ_API_KEY'])
    summarizer_agent = SummarizerAgent(groq_client)
    action_agent = ActionAgent(groq_client)
    
    @app.route('/')
    def landing():
        """Landing page"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('landing.html')
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """User registration"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            
            # Check if user already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'error')
                return render_template('register.html')
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'error')
                return render_template('register.html')
            
            # Create new user
            user = User(username=username, email=email)
            user.set_password(password)
            
            try:
                db.session.add(user)
                db.session.commit()
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                flash('Registration failed. Please try again.', 'error')
        
        return render_template('register.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            remember = bool(request.form.get('remember'))
            
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user, remember=remember)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
        
        return render_template('login.html')
    
    @app.route('/logout')
    @login_required
    def logout():
        """User logout"""
        logout_user()
        return redirect(url_for('landing'))
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Main dashboard showing meetings and action items"""
        page = request.args.get('page', 1, type=int)
        meetings = Meeting.query.filter_by(user_id=current_user.id)\
                              .order_by(Meeting.created_at.desc())\
                              .paginate(page=page, per_page=app.config['MEETINGS_PER_PAGE'], error_out=False)
        
        # Get recent action items
        recent_action_items = ActionItem.query.join(Meeting)\
                                            .filter(Meeting.user_id == current_user.id)\
                                            .order_by(ActionItem.created_at.desc())\
                                            .limit(10).all()
        
        return render_template('dashboard.html', 
                             meetings=meetings, 
                             recent_action_items=recent_action_items)
    
    @app.route('/upload', methods=['GET', 'POST'])
    @login_required
    def upload():
        """Upload meeting transcript"""
        if request.method == 'POST':
            title = request.form['title']
            description = request.form.get('description', '')
            participants = request.form.get('participants', '')
            meeting_link = request.form.get('meeting_link', '')
            transcript_text = request.form.get('transcript_text', '')
            
            # Handle file upload
            if 'transcript_file' in request.files:
                file = request.files['transcript_file']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    transcript_text = parse_transcript_file(filepath)
                    os.remove(filepath)  # Clean up uploaded file
            
            if not transcript_text.strip():
                flash('Please provide a transcript', 'error')
                return render_template('upload.html')
            
            # Create meeting record
            meeting = Meeting(
                title=title,
                description=description,
                transcript=transcript_text,
                meeting_link=meeting_link,
                participants=participants,
                user_id=current_user.id
            )
            
            try:
                db.session.add(meeting)
                db.session.commit()
                
                # Process with AI agents
                try:
                    # Generate summary
                    summary = summarizer_agent.summarize_meeting(transcript_text)
                    meeting.summary = summary
                    
                    # Extract action items
                    action_items_data = action_agent.extract_action_items(transcript_text)
                    
                    # Create action item records
                    for item_data in action_items_data:
                        action_item = ActionItem(
                            title=item_data['title'],
                            description=item_data.get('description', ''),
                            assignee=item_data.get('assignee', ''),
                            due_date=datetime.fromisoformat(item_data['due_date']) if item_data.get('due_date') else None,
                            priority=item_data.get('priority', 'medium'),
                            meeting_id=meeting.id
                        )
                        db.session.add(action_item)
                    
                    db.session.commit()
                    flash('Meeting processed successfully!', 'success')
                    
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error processing meeting with AI: {str(e)}', 'error')
                    return redirect(url_for('meeting_detail', meeting_id=meeting.id))
                
                return redirect(url_for('meeting_detail', meeting_id=meeting.id))
                
            except Exception as e:
                db.session.rollback()
                flash('Error saving meeting', 'error')
        
        return render_template('upload.html')
    
    @app.route('/meeting/<int:meeting_id>')
    @login_required
    def meeting_detail(meeting_id):
        """View meeting details"""
        meeting = Meeting.query.filter_by(id=meeting_id, user_id=current_user.id).first_or_404()
        return render_template('meeting_detail.html', meeting=meeting)
    
    @app.route('/action_items')
    @login_required
    def action_items():
        """View all action items"""
        page = request.args.get('page', 1, type=int)
        status_filter = request.args.get('status', 'all')
        priority_filter = request.args.get('priority', 'all')
        
        query = ActionItem.query.join(Meeting).filter(Meeting.user_id == current_user.id)
        
        if status_filter != 'all':
            query = query.filter(ActionItem.status == status_filter)
        
        if priority_filter != 'all':
            query = query.filter(ActionItem.priority == priority_filter)
        
        action_items = query.order_by(ActionItem.due_date.asc())\
                          .paginate(page=page, per_page=app.config['ACTION_ITEMS_PER_PAGE'], error_out=False)
        
        return render_template('action_items.html', 
                             action_items=action_items,
                             status_filter=status_filter,
                             priority_filter=priority_filter)
    
    @app.route('/api/action_items/<int:action_item_id>/status', methods=['PUT'])
    @login_required
    def update_action_item_status(action_item_id):
        """Update action item status via API"""
        action_item = ActionItem.query.join(Meeting)\
                                    .filter(ActionItem.id == action_item_id, 
                                           Meeting.user_id == current_user.id).first_or_404()
        
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status in ['pending', 'in_progress', 'completed', 'cancelled']:
            action_item.status = new_status
            action_item.updated_at = datetime.utcnow()
            
            try:
                db.session.commit()
                return jsonify({'success': True, 'status': new_status})
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'error': str(e)}), 500
        
        return jsonify({'success': False, 'error': 'Invalid status'}), 400
    
    @app.route('/api/action_items/timeline')
    @login_required
    def action_items_timeline():
        """Get action items timeline data for visualization"""
        timeline_data = generate_action_timeline_data(current_user.id)
        return jsonify(timeline_data)
    
    @app.route('/api/meetings/recording', methods=['POST'])
    @login_required
    def upload_recording():
        """Accept browser-recorded audio, transcribe, and create meeting + tasks."""
        if 'audio' not in request.files:
            return jsonify({'success': False, 'error': 'No audio file provided'}), 400
        audio = request.files['audio']
        if not audio or not audio.filename:
            return jsonify({'success': False, 'error': 'Invalid audio'}), 400
        
        title = request.form.get('title', 'Recorded Meeting')
        description = request.form.get('description', '')
        participants = request.form.get('participants', '')
        meeting_link = request.form.get('meeting_link', '')
        
        # Save temp audio
        filename = secure_filename(audio.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        audio.save(temp_path)
        
        try:
            # Transcribe
            transcript_text = transcribe_audio_faster_whisper(temp_path)
            if not transcript_text.strip():
                raise Exception('Empty transcription')
            
            # Create meeting
            meeting = Meeting(
                title=title,
                description=description,
                meeting_link=meeting_link,
                transcript=transcript_text,
                participants=participants,
                transcript_source='recording',
                user_id=current_user.id,
                audio_path=filename
            )
            db.session.add(meeting)
            db.session.commit()
            
            # Process with AI agents
            try:
                summary = summarizer_agent.summarize_meeting(transcript_text)
                meeting.summary = summary
                action_items_data = action_agent.extract_action_items(transcript_text)
                for item_data in action_items_data:
                    action_item = ActionItem(
                        title=item_data['title'],
                        description=item_data.get('description', ''),
                        assignee=item_data.get('assignee', ''),
                        due_date=datetime.fromisoformat(item_data['due_date']) if item_data.get('due_date') else None,
                        priority=item_data.get('priority', 'medium'),
                        meeting_id=meeting.id
                    )
                    db.session.add(action_item)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'error': f'AI processing failed: {str(e)}'}), 500
            
            return jsonify({'success': True, 'meeting_id': meeting.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

    @app.route('/api/google/create_meet_link', methods=['POST'])
    @login_required
    def create_meet_link():
        """Create a Google Calendar event with a Meet link and attach it to a meeting."""
        data = request.get_json(force=True)
        meeting_id = data.get('meeting_id')
        attendees = data.get('attendees', [])
        summary = data.get('summary', 'Meeting')
        description = data.get('description', '')
        
        meeting = Meeting.query.filter_by(id=meeting_id, user_id=current_user.id).first_or_404()
        try:
            event_id, meet_link = create_google_meet_event(
                summary=summary or meeting.title,
                description=description or meeting.description or '',
                attendees_emails=attendees
            )
            meeting.meeting_link = meet_link
            db.session.commit()
            return jsonify({ 'success': True, 'event_id': event_id, 'meet_link': meet_link })
        except Exception as e:
            db.session.rollback()
            return jsonify({ 'success': False, 'error': str(e) }), 500

    @app.route('/api/meetings/process_link', methods=['POST'])
    @login_required
    async def process_meeting_link():
        """Process a meeting link (Zoom, Teams, etc.) and join/record the meeting asynchronously."""
        data = request.get_json()
        meeting_url = data.get('meeting_url', '').strip()
        title = data.get('title', 'Meeting')
        description = data.get('description', '')
        participants = data.get('participants', '')
        duration_minutes = data.get('duration_minutes', 60)

        if not meeting_url:
            return jsonify({'success': False, 'error': 'Meeting URL is required'}), 400

        if 'zoom.us' in meeting_url:
            try:
                meeting_info = extract_meeting_info_from_url(meeting_url)
                if not meeting_info['valid']:
                    return jsonify({'success': False, 'error': meeting_info['message']}), 400

                result = await asyncio.to_thread(process_zoom_meeting, meeting_url, duration_minutes)

                if result['success']:
                    meeting = Meeting(
                        title=title,
                        description=description,
                        meeting_link=meeting_url,
                        participants=participants,
                        transcript=result.get('transcript', ''),
                        transcript_source='zoom_recording',
                        audio_path=result.get('recording_path', ''),
                        user_id=current_user.id
                    )
                    db.session.add(meeting)
                    db.session.commit()

                    if result.get('transcript'):
                        try:
                            summary = await asyncio.to_thread(summarizer_agent.summarize_meeting, result['transcript'])
                            meeting.summary = summary

                            action_items_data = await asyncio.to_thread(
                                action_agent.extract_action_items, result['transcript']
                            )
                            for item_data in action_items_data:
                                action_item = ActionItem(
                                    title=item_data['title'],
                                    description=item_data.get('description', ''),
                                    assignee=item_data.get('assignee', ''),
                                    due_date=datetime.fromisoformat(item_data['due_date']) if item_data.get('due_date') else None,
                                    priority=item_data.get('priority', 'medium'),
                                    meeting_id=meeting.id
                                )
                                db.session.add(action_item)
                            db.session.commit()
                        except Exception as e:
                            db.session.rollback()
                            return jsonify({'success': False, 'error': f'AI processing error: {str(e)}'}), 500

                    return jsonify({
                        'success': True,
                        'message': 'Meeting processed successfully.',
                        'meeting_info': meeting_info,
                        'meeting_id': meeting.id
                    })
                else:
                    return jsonify({'success': False, 'error': 'Zoom meeting processing failed'}), 500

            except Exception as e:
                return jsonify({'success': False, 'error': f'Error processing Zoom meeting: {str(e)}'}), 500

        else:
            # Other platforms
            try:
                meeting = Meeting(
                    title=title,
                    description=description,
                    meeting_link=meeting_url,
                    participants=participants,
                    transcript='Meeting link added - manual processing required',
                    user_id=current_user.id
                )
                db.session.add(meeting)
                db.session.commit()
                return jsonify({
                    'success': True,
                    'message': 'Meeting link saved. Please add transcript manually.',
                    'meeting_id': meeting.id
                })
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'error': f'Error saving meeting: {str(e)}'}), 500

    @app.route('/api/meetings/validate_link', methods=['POST'])
    @login_required
    def validate_meeting_link():
        """Validate a meeting link and extract information."""
        data = request.get_json()
        meeting_url = data.get('meeting_url', '').strip()
        
        if not meeting_url:
            return jsonify({'valid': False, 'error': 'Meeting URL is required'}), 400
        
        try:
            if 'zoom.us' in meeting_url:
                meeting_info = extract_meeting_info_from_url(meeting_url)
                return jsonify(meeting_info)
            else:
                return jsonify({
                    'valid': True,
                    'platform': 'Other',
                    'url': meeting_url,
                    'message': 'Meeting link validated (manual processing required)'
                })
        except Exception as e:
            return jsonify({'valid': False, 'error': f'Error validating link: {str(e)}'}), 500

    @app.route('/api/meetings/status')
    @login_required
    def meeting_status():
        """Get current meeting processing status."""
        try:
            # Check for recent meetings that might be processing
            recent_meetings = Meeting.query.filter_by(user_id=current_user.id)\
                                         .filter(Meeting.transcript_source == 'zoom_recording')\
                                         .order_by(Meeting.created_at.desc())\
                                         .limit(5).all()
            
            processing_meetings = []
            for meeting in recent_meetings:
                if not meeting.summary and meeting.transcript_source == 'zoom_recording':
                    processing_meetings.append({
                        'id': meeting.id,
                        'title': meeting.title,
                        'created_at': meeting.created_at.isoformat()
                    })
            
            if processing_meetings:
                return jsonify({
                    'processing': True,
                    'message': f'{len(processing_meetings)} meeting(s) being processed',
                    'meetings': processing_meetings
                })
            else:
                return jsonify({
                    'processing': False,
                    'message': 'No meetings currently being processed'
                })
                
        except Exception as e:
            return jsonify({
                'processing': False,
                'error': f'Error checking status: {str(e)}'
            }), 500


    return app   
    