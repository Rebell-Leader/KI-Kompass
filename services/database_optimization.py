import logging
from sqlalchemy import Index, text
from app import db
from models import User, IntegrationPipeline, ActionStep, TaskStatus, ChatMessage

logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    """
    Database optimization service for improving query performance
    """
    
    @staticmethod
    def create_performance_indexes():
        """
        Create database indexes for commonly queried fields
        """
        try:
            with db.engine.connect() as conn:
                # Users table indexes
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_users_email 
                    ON users(email);
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_users_onboarded 
                    ON users(onboarded);
                """))
                
                # Integration pipelines indexes
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_pipelines_user_id 
                    ON integration_pipelines(user_id);
                """))
                
                # Task statuses indexes for common queries
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_task_statuses_pipeline_id 
                    ON task_statuses(pipeline_id);
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_task_statuses_action_step_id 
                    ON task_statuses(action_step_id);
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_task_statuses_completed 
                    ON task_statuses(completed);
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_task_statuses_deadline 
                    ON task_statuses(deadline) WHERE deadline IS NOT NULL;
                """))
                
                # Composite index for dashboard queries
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_task_statuses_pipeline_completed 
                    ON task_statuses(pipeline_id, completed);
                """))
                
                # Action steps indexes
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_action_steps_category 
                    ON action_steps(category);
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_action_steps_priority 
                    ON action_steps(priority);
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_action_steps_family_required 
                    ON action_steps(family_required);
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_action_steps_employment_required 
                    ON action_steps(employment_required);
                """))
                
                # Chat messages indexes
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id 
                    ON chat_messages(user_id);
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_id 
                    ON chat_messages(conversation_id);
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at 
                    ON chat_messages(created_at);
                """))
                
                # Composite index for conversation queries
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_chat_messages_user_conversation 
                    ON chat_messages(user_id, conversation_id, created_at);
                """))
                
                conn.commit()
                logger.info("Database performance indexes created successfully")
                
        except Exception as e:
            logger.error(f"Error creating database indexes: {str(e)}")
            raise e
    
    @staticmethod
    def optimize_dashboard_query(user_id):
        """
        Optimized query for dashboard data to reduce N+1 problems
        """
        try:
            # Single query to get all dashboard data
            result = db.session.execute(text("""
                SELECT 
                    p.id as pipeline_id,
                    p.title as pipeline_title,
                    p.progress as pipeline_progress,
                    p.updated_at as pipeline_updated,
                    a.id as action_id,
                    a.title as action_title,
                    a.description as action_description,
                    a.category as action_category,
                    a.priority as action_priority,
                    a.estimated_time as action_estimated_time,
                    a.required_documents as action_documents,
                    ts.id as task_status_id,
                    ts.completed as task_completed,
                    ts.completion_date as task_completion_date,
                    ts.deadline as task_deadline,
                    ts.notes as task_notes,
                    CASE 
                        WHEN ts.deadline IS NOT NULL AND ts.deadline < NOW() AND ts.completed = false 
                        THEN true 
                        ELSE false 
                    END as is_overdue
                FROM integration_pipelines p
                LEFT JOIN task_statuses ts ON p.id = ts.pipeline_id
                LEFT JOIN action_steps a ON ts.action_step_id = a.id
                WHERE p.user_id = :user_id
                ORDER BY 
                    ts.completed ASC,
                    ts.deadline ASC NULLS LAST,
                    a.priority ASC
            """), {"user_id": user_id})
            
            # Process results into structured data
            dashboard_data = {
                "pipeline": None,
                "tasks": [],
                "stats": {
                    "total": 0,
                    "completed": 0,
                    "pending": 0,
                    "overdue": 0
                }
            }
            
            for row in result:
                if not dashboard_data["pipeline"] and row.pipeline_id:
                    dashboard_data["pipeline"] = {
                        "id": row.pipeline_id,
                        "title": row.pipeline_title,
                        "progress": row.pipeline_progress,
                        "updated_at": row.pipeline_updated
                    }
                
                if row.action_id:
                    task_data = {
                        "action_step": {
                            "id": row.action_id,
                            "title": row.action_title,
                            "description": row.action_description,
                            "category": row.action_category,
                            "priority": row.action_priority,
                            "estimated_time": row.action_estimated_time,
                            "required_documents": row.action_documents
                        },
                        "task_status": {
                            "id": row.task_status_id,
                            "completed": row.task_completed,
                            "completion_date": row.task_completion_date,
                            "deadline": row.task_deadline,
                            "notes": row.task_notes,
                            "is_overdue": row.is_overdue
                        }
                    }
                    
                    dashboard_data["tasks"].append(task_data)
                    dashboard_data["stats"]["total"] += 1
                    
                    if row.task_completed:
                        dashboard_data["stats"]["completed"] += 1
                    else:
                        dashboard_data["stats"]["pending"] += 1
                        if row.is_overdue:
                            dashboard_data["stats"]["overdue"] += 1
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error in optimized dashboard query: {str(e)}")
            raise e
    
    @staticmethod
    def get_user_notifications_optimized(user_id):
        """
        Optimized query for user notifications
        """
        try:
            # Single query to get overdue and upcoming tasks
            result = db.session.execute(text("""
                SELECT 
                    a.id as action_id,
                    a.title as action_title,
                    a.category as action_category,
                    ts.deadline as task_deadline,
                    ts.completed as task_completed,
                    CASE 
                        WHEN ts.deadline < NOW() AND ts.completed = false 
                        THEN 'overdue'
                        WHEN ts.deadline BETWEEN NOW() AND NOW() + INTERVAL '7 days' AND ts.completed = false
                        THEN 'upcoming'
                        ELSE 'normal'
                    END as urgency_type,
                    EXTRACT(DAY FROM (ts.deadline - NOW()))::integer as days_diff
                FROM integration_pipelines p
                JOIN task_statuses ts ON p.id = ts.pipeline_id
                JOIN action_steps a ON ts.action_step_id = a.id
                WHERE p.user_id = :user_id
                AND ts.completed = false
                AND ts.deadline IS NOT NULL
                AND ts.deadline <= NOW() + INTERVAL '7 days'
                ORDER BY ts.deadline ASC
            """), {"user_id": user_id})
            
            notifications = []
            for row in result:
                if row.urgency_type == 'overdue':
                    notifications.append({
                        'id': f"overdue_{row.action_id}",
                        'type': 'overdue',
                        'priority': 1,
                        'title': f"Overdue Task: {row.action_title}",
                        'message': f"This task was due {abs(row.days_diff)} days ago.",
                        'action_url': f'/dashboard#task-{row.action_id}',
                        'timestamp': row.task_deadline.isoformat() if row.task_deadline else None,
                        'category': row.action_category,
                        'task_id': row.action_id
                    })
                elif row.urgency_type == 'upcoming':
                    urgency = "today" if row.days_diff == 0 else f"in {row.days_diff} days"
                    priority = 1 if row.days_diff <= 1 else 2 if row.days_diff <= 3 else 3
                    
                    notifications.append({
                        'id': f"upcoming_{row.action_id}",
                        'type': 'upcoming',
                        'priority': priority,
                        'title': f"Upcoming: {row.action_title}",
                        'message': f"This task is due {urgency}.",
                        'action_url': f'/dashboard#task-{row.action_id}',
                        'timestamp': row.task_deadline.isoformat() if row.task_deadline else None,
                        'category': row.action_category,
                        'task_id': row.action_id
                    })
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error in optimized notifications query: {str(e)}")
            return []
    
    @staticmethod
    def analyze_query_performance():
        """
        Analyze database query performance and suggest optimizations
        """
        try:
            with db.engine.connect() as conn:
                # Check for missing indexes
                result = conn.execute(text("""
                    SELECT 
                        schemaname,
                        tablename,
                        attname,
                        n_distinct,
                        correlation
                    FROM pg_stats 
                    WHERE schemaname = 'public'
                    AND n_distinct > 100
                    ORDER BY tablename, n_distinct DESC;
                """))
                
                performance_stats = []
                for row in result:
                    performance_stats.append({
                        "table": row.tablename,
                        "column": row.attname,
                        "distinct_values": row.n_distinct,
                        "correlation": row.correlation
                    })
                
                return performance_stats
                
        except Exception as e:
            logger.error(f"Error analyzing query performance: {str(e)}")
            return []
    
    @staticmethod
    def cleanup_old_data():
        """
        Clean up old data to maintain database performance
        """
        try:
            with db.engine.connect() as conn:
                # Clean up old chat messages (keep last 1000 per user)
                conn.execute(text("""
                    DELETE FROM chat_messages 
                    WHERE id NOT IN (
                        SELECT id FROM (
                            SELECT id, ROW_NUMBER() OVER (
                                PARTITION BY user_id 
                                ORDER BY created_at DESC
                            ) as rn
                            FROM chat_messages
                        ) t 
                        WHERE rn <= 1000
                    );
                """))
                
                # Clean up incomplete user registrations older than 7 days
                conn.execute(text("""
                    DELETE FROM users 
                    WHERE onboarded = false 
                    AND created_at < NOW() - INTERVAL '7 days';
                """))
                
                conn.commit()
                logger.info("Database cleanup completed successfully")
                
        except Exception as e:
            logger.error(f"Error during database cleanup: {str(e)}")
            raise e