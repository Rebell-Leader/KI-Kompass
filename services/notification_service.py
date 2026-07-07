import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from models import User, TaskStatus, ActionStep
from app import db

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Notification service for managing user alerts and reminders.
    Currently implements popup notifications with preparation for email/SMS integration.
    """
    
    @staticmethod
    def get_user_notifications(user_id: int) -> List[Dict]:
        """
        Get all pending notifications for a user
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return []
            
            notifications = []
            
            # Check for overdue tasks
            overdue_notifications = NotificationService._get_overdue_task_notifications(user_id)
            notifications.extend(overdue_notifications)
            
            # Check for upcoming deadlines
            upcoming_notifications = NotificationService._get_upcoming_deadline_notifications(user_id)
            notifications.extend(upcoming_notifications)
            
            # Check for welcome/onboarding notifications
            welcome_notifications = NotificationService._get_welcome_notifications(user)
            notifications.extend(welcome_notifications)
            
            # Sort by priority and timestamp
            notifications.sort(key=lambda x: (x.get('priority', 3), x.get('timestamp', datetime.now())), reverse=True)
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error getting notifications for user {user_id}: {str(e)}")
            return []
    
    @staticmethod
    def _get_overdue_task_notifications(user_id: int) -> List[Dict]:
        """
        Get notifications for overdue tasks
        """
        try:
            from models import IntegrationPipeline
            
            pipeline = IntegrationPipeline.query.filter_by(user_id=user_id).first()
            if not pipeline:
                return []
            
            # Find overdue tasks
            overdue_tasks = db.session.query(TaskStatus, ActionStep).join(
                ActionStep, TaskStatus.action_step_id == ActionStep.id
            ).filter(
                TaskStatus.pipeline_id == pipeline.id,
                TaskStatus.completed == False,
                TaskStatus.deadline < datetime.utcnow()
            ).all()
            
            notifications = []
            for task_status, action_step in overdue_tasks:
                days_overdue = (datetime.utcnow() - task_status.deadline).days
                
                notifications.append({
                    'id': f"overdue_{task_status.id}",
                    'type': 'overdue',
                    'priority': 1,  # High priority
                    'title': f"Overdue Task: {action_step.title}",
                    'message': f"This task was due {days_overdue} days ago. Please complete it as soon as possible.",
                    'action_url': '/dashboard#task-' + str(action_step.id),
                    'timestamp': task_status.deadline,
                    'category': action_step.category,
                    'task_id': action_step.id
                })
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error getting overdue notifications: {str(e)}")
            return []
    
    @staticmethod
    def _get_upcoming_deadline_notifications(user_id: int) -> List[Dict]:
        """
        Get notifications for upcoming deadlines (within 7 days)
        """
        try:
            from models import IntegrationPipeline
            
            pipeline = IntegrationPipeline.query.filter_by(user_id=user_id).first()
            if not pipeline:
                return []
            
            # Find tasks due within 7 days
            upcoming_deadline = datetime.utcnow() + timedelta(days=7)
            upcoming_tasks = db.session.query(TaskStatus, ActionStep).join(
                ActionStep, TaskStatus.action_step_id == ActionStep.id
            ).filter(
                TaskStatus.pipeline_id == pipeline.id,
                TaskStatus.completed == False,
                TaskStatus.deadline.between(datetime.utcnow(), upcoming_deadline)
            ).all()
            
            notifications = []
            for task_status, action_step in upcoming_tasks:
                days_until_due = (task_status.deadline - datetime.utcnow()).days
                
                if days_until_due <= 1:
                    urgency = "tomorrow" if days_until_due == 1 else "today"
                    priority = 1
                elif days_until_due <= 3:
                    urgency = f"in {days_until_due} days"
                    priority = 2
                else:
                    urgency = f"in {days_until_due} days"
                    priority = 3
                
                notifications.append({
                    'id': f"upcoming_{task_status.id}",
                    'type': 'upcoming',
                    'priority': priority,
                    'title': f"Upcoming: {action_step.title}",
                    'message': f"This task is due {urgency}. Don't forget to complete it!",
                    'action_url': '/dashboard#task-' + str(action_step.id),
                    'timestamp': task_status.deadline,
                    'category': action_step.category,
                    'task_id': action_step.id
                })
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error getting upcoming deadline notifications: {str(e)}")
            return []
    
    @staticmethod
    def _get_welcome_notifications(user: User) -> List[Dict]:
        """
        Get welcome and onboarding notifications
        """
        notifications = []
        
        try:
            # Welcome message for new users
            if user.created_at is not None and (datetime.utcnow() - user.created_at).days < 1:
                notifications.append({
                    'id': f"welcome_{user.id}",
                    'type': 'welcome',
                    'priority': 2,
                    'title': "Welcome to KI Kompass!",
                    'message': "Your personalized Munich relocation assistant is ready to help you. Start by checking your dashboard!",
                    'action_url': '/dashboard',
                    'timestamp': user.created_at
                })
            
            # Onboarding completion reminder
            if user.onboarded == False:
                notifications.append({
                    'id': f"onboarding_{user.id}",
                    'type': 'onboarding',
                    'priority': 1,
                    'title': "Complete Your Profile",
                    'message': "Please complete your profile to get personalized relocation guidance.",
                    'action_url': '/onboarding',
                    'timestamp': user.created_at
                })
            
            # AI Assistant introduction
            if user.onboarded == True and not hasattr(user, 'has_used_chat'):
                notifications.append({
                    'id': f"ai_intro_{user.id}",
                    'type': 'feature',
                    'priority': 3,
                    'title': "Try the AI Assistant",
                    'message': "Ask me any questions about relocating to Munich. I'm here to help!",
                    'action_url': '/chat',
                    'timestamp': datetime.utcnow()
                })
            
        except Exception as e:
            logger.error(f"Error getting welcome notifications: {str(e)}")
        
        return notifications
    
    @staticmethod
    def mark_notification_read(user_id: int, notification_id: str) -> bool:
        """
        Mark a notification as read (for future implementation with database storage)
        """
        try:
            # For now, just log the action
            logger.info(f"User {user_id} marked notification {notification_id} as read")
            return True
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            return False
    
    @staticmethod
    def send_email_notification(user_id: int, notification: Dict) -> bool:
        """
        Send a single notification by email (SMTP configured via env vars;
        see services/email_service.py). Daily digests are handled by
        'flask send-reminders'.
        """
        try:
            user = db.session.get(User, user_id)
            if not user or not user.email:
                return False

            from services.email_service import send_email
            return send_email(
                user.email,
                f"KI Kompass: {notification['title']}",
                notification.get('message', '')
            )
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return False
    
    @staticmethod
    def send_sms_notification(user_id: int, notification: Dict) -> bool:
        """
        Send SMS notification (placeholder for future implementation)
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False
            
            # Placeholder for SMS service integration
            logger.info(f"Would send SMS to user {user_id}: {notification['title']}")
            
            # Future implementation would integrate with services like:
            # - Twilio
            # - AWS SNS
            # - MessageBird
            
            return True
        except Exception as e:
            logger.error(f"Error sending SMS notification: {str(e)}")
            return False