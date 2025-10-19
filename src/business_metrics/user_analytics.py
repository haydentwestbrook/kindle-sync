"""
User analytics for the Kindle Sync application.

Tracks user behavior and engagement metrics.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass
from loguru import logger


@dataclass
class UserActivity:
    """Represents user activity data."""
    user_id: str
    timestamp: datetime
    activity_type: str
    metadata: Dict[str, Any]


class UserAnalytics:
    """Collects and analyzes user behavior data."""
    
    def __init__(self):
        """Initialize user analytics."""
        self.user_activities: List[UserActivity] = []
        self.user_sessions: Dict[str, List[datetime]] = defaultdict(list)
        self.user_metrics: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        logger.info("User analytics initialized")
    
    def record_activity(self, user_id: str, activity_type: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Record user activity.
        
        Args:
            user_id: Unique user identifier
            activity_type: Type of activity
            metadata: Additional activity metadata
        """
        activity = UserActivity(
            user_id=user_id,
            timestamp=datetime.utcnow(),
            activity_type=activity_type,
            metadata=metadata or {}
        )
        
        self.user_activities.append(activity)
        self.user_sessions[user_id].append(activity.timestamp)
        
        logger.debug(f"Recorded activity for user {user_id}: {activity_type}")
    
    def get_user_engagement(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get user engagement metrics.
        
        Args:
            user_id: User identifier
            days: Number of days to analyze
            
        Returns:
            User engagement metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Filter activities for this user and time period
        user_activities = [
            activity for activity in self.user_activities
            if activity.user_id == user_id and activity.timestamp >= cutoff_date
        ]
        
        if not user_activities:
            return {
                "user_id": user_id,
                "total_activities": 0,
                "active_days": 0,
                "average_activities_per_day": 0,
                "most_common_activity": None,
                "last_activity": None
            }
        
        # Calculate metrics
        total_activities = len(user_activities)
        active_days = len(set(activity.timestamp.date() for activity in user_activities))
        average_activities_per_day = total_activities / max(1, active_days)
        
        # Most common activity type
        activity_counts = defaultdict(int)
        for activity in user_activities:
            activity_counts[activity.activity_type] += 1
        
        most_common_activity = max(activity_counts.items(), key=lambda x: x[1])[0] if activity_counts else None
        
        # Last activity
        last_activity = max(user_activities, key=lambda x: x.timestamp).timestamp
        
        return {
            "user_id": user_id,
            "total_activities": total_activities,
            "active_days": active_days,
            "average_activities_per_day": round(average_activities_per_day, 2),
            "most_common_activity": most_common_activity,
            "last_activity": last_activity.isoformat(),
            "activity_breakdown": dict(activity_counts)
        }
    
    def get_daily_active_users(self, date: Optional[datetime] = None) -> int:
        """
        Get number of daily active users for a specific date.
        
        Args:
            date: Date to analyze (defaults to today)
            
        Returns:
            Number of daily active users
        """
        if date is None:
            date = datetime.utcnow().date()
        
        active_users = set()
        for activity in self.user_activities:
            if activity.timestamp.date() == date:
                active_users.add(activity.user_id)
        
        return len(active_users)
    
    def get_retention_metrics(self, cohort_date: datetime, days: int = 7) -> Dict[str, Any]:
        """
        Calculate user retention metrics for a cohort.
        
        Args:
            cohort_date: Date of the cohort
            days: Number of days to track retention
            
        Returns:
            Retention metrics
        """
        # Get users who were active on cohort date
        cohort_users = set()
        for activity in self.user_activities:
            if activity.timestamp.date() == cohort_date.date():
                cohort_users.add(activity.user_id)
        
        if not cohort_users:
            return {
                "cohort_date": cohort_date.date().isoformat(),
                "cohort_size": 0,
                "retention_rates": {}
            }
        
        # Calculate retention for each day
        retention_rates = {}
        for day in range(1, days + 1):
            target_date = cohort_date + timedelta(days=day)
            
            # Count users who were active on target date
            retained_users = set()
            for activity in self.user_activities:
                if (activity.user_id in cohort_users and 
                    activity.timestamp.date() == target_date.date()):
                    retained_users.add(activity.user_id)
            
            retention_rate = len(retained_users) / len(cohort_users) * 100
            retention_rates[f"day_{day}"] = round(retention_rate, 2)
        
        return {
            "cohort_date": cohort_date.date().isoformat(),
            "cohort_size": len(cohort_users),
            "retention_rates": retention_rates
        }
    
    def get_activity_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get overall activity summary.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Activity summary
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Filter recent activities
        recent_activities = [
            activity for activity in self.user_activities
            if activity.timestamp >= cutoff_date
        ]
        
        if not recent_activities:
            return {
                "total_activities": 0,
                "unique_users": 0,
                "average_activities_per_user": 0,
                "most_active_users": [],
                "activity_breakdown": {}
            }
        
        # Calculate metrics
        total_activities = len(recent_activities)
        unique_users = len(set(activity.user_id for activity in recent_activities))
        average_activities_per_user = total_activities / max(1, unique_users)
        
        # Most active users
        user_activity_counts = defaultdict(int)
        for activity in recent_activities:
            user_activity_counts[activity.user_id] += 1
        
        most_active_users = sorted(
            user_activity_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Activity breakdown
        activity_breakdown = defaultdict(int)
        for activity in recent_activities:
            activity_breakdown[activity.activity_type] += 1
        
        return {
            "total_activities": total_activities,
            "unique_users": unique_users,
            "average_activities_per_user": round(average_activities_per_user, 2),
            "most_active_users": most_active_users,
            "activity_breakdown": dict(activity_breakdown)
        }
    
    def cleanup_old_data(self, days: int = 90):
        """
        Clean up old activity data.
        
        Args:
            days: Keep data for this many days
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Remove old activities
        self.user_activities = [
            activity for activity in self.user_activities
            if activity.timestamp >= cutoff_date
        ]
        
        # Clean up user sessions
        for user_id in list(self.user_sessions.keys()):
            self.user_sessions[user_id] = [
                timestamp for timestamp in self.user_sessions[user_id]
                if timestamp >= cutoff_date
            ]
            
            # Remove empty user sessions
            if not self.user_sessions[user_id]:
                del self.user_sessions[user_id]
        
        logger.info(f"Cleaned up activity data older than {days} days")
