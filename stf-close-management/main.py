#!/usr/bin/env python3
"""
D6E Docker STF: Close Management

Overview:
    Manages month-end close process including:
    - Close task tracking and status management
    - Task dependency and sequencing
    - Close calendar generation
    - Progress monitoring and reporting
    - Blocker identification and escalation

Main Operations:
    - initialize_close_tasks: Set up close tasks for a period
    - update_task_status: Update status of a close task
    - get_close_progress: Get overall close progress
    - identify_blockers: Find blocked tasks and dependencies
    - generate_close_calendar: Create close calendar with deadlines
    - get_critical_path: Identify critical path tasks

Limitations:
    - Does not send notifications (returns notification data only)
    - Calendar assumes 5-day close by default
    - Does not integrate with external project management tools
"""

import sys
import os
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

from utils import (
    logger, readInput, writeOutput, writeError,
    createApiClient, validateRequiredFields
)


class CloseManager:
    """
    Manages month-end close process and task tracking.
    """
    
    # Standard close task templates
    STANDARD_CLOSE_TASKS = [
        # Day 1 (T+1)
        {"name": "Record cash receipts and disbursements", "category": "CASH", "day": 1, "dependencies": []},
        {"name": "Post payroll entries", "category": "PAYROLL", "day": 1, "dependencies": []},
        {"name": "Run AP accruals", "category": "ACCRUALS", "day": 1, "dependencies": []},
        {"name": "Run fixed asset depreciation", "category": "DEPRECIATION", "day": 1, "dependencies": []},
        {"name": "Post prepaid amortization", "category": "AMORTIZATION", "day": 1, "dependencies": []},
        {"name": "Post intercompany transactions", "category": "INTERCOMPANY", "day": 1, "dependencies": []},
        
        # Day 2 (T+2)
        {"name": "Complete bank reconciliation", "category": "RECONCILIATION", "day": 2, "dependencies": ["Record cash receipts and disbursements"]},
        {"name": "Post revenue recognition entries", "category": "REVENUE", "day": 2, "dependencies": []},
        {"name": "Complete AR subledger reconciliation", "category": "RECONCILIATION", "day": 2, "dependencies": ["Post revenue recognition entries"]},
        {"name": "Complete AP subledger reconciliation", "category": "RECONCILIATION", "day": 2, "dependencies": ["Run AP accruals"]},
        {"name": "Post FX revaluation entries", "category": "FX", "day": 2, "dependencies": []},
        {"name": "Post remaining accrual entries", "category": "ACCRUALS", "day": 2, "dependencies": []},
        
        # Day 3 (T+3)
        {"name": "Complete all balance sheet reconciliations", "category": "RECONCILIATION", "day": 3, "dependencies": ["Complete bank reconciliation", "Complete AR subledger reconciliation", "Complete AP subledger reconciliation"]},
        {"name": "Complete intercompany reconciliation", "category": "INTERCOMPANY", "day": 3, "dependencies": ["Post intercompany transactions"]},
        {"name": "Post reconciliation adjustments", "category": "ADJUSTMENTS", "day": 3, "dependencies": ["Complete all balance sheet reconciliations"]},
        {"name": "Run preliminary trial balance", "category": "REPORTING", "day": 3, "dependencies": ["Post reconciliation adjustments"]},
        {"name": "Perform preliminary flux analysis", "category": "ANALYSIS", "day": 3, "dependencies": ["Run preliminary trial balance"]},
        
        # Day 4 (T+4)
        {"name": "Post tax provision entries", "category": "TAX", "day": 4, "dependencies": ["Run preliminary trial balance"]},
        {"name": "Complete equity roll-forward", "category": "EQUITY", "day": 4, "dependencies": []},
        {"name": "Generate draft financial statements", "category": "REPORTING", "day": 4, "dependencies": ["Post tax provision entries", "Complete equity roll-forward"]},
        {"name": "Perform detailed flux analysis", "category": "ANALYSIS", "day": 4, "dependencies": ["Generate draft financial statements"]},
        {"name": "Management review of financials", "category": "REVIEW", "day": 4, "dependencies": ["Perform detailed flux analysis"]},
        
        # Day 5 (T+5)
        {"name": "Post final adjustments", "category": "ADJUSTMENTS", "day": 5, "dependencies": ["Management review of financials"]},
        {"name": "Finalize financial statements", "category": "REPORTING", "day": 5, "dependencies": ["Post final adjustments"]},
        {"name": "Lock period in system", "category": "CLOSE", "day": 5, "dependencies": ["Finalize financial statements"]},
        {"name": "Distribute reporting package", "category": "REPORTING", "day": 5, "dependencies": ["Lock period in system"]},
        {"name": "Conduct close retrospective", "category": "PROCESS", "day": 5, "dependencies": ["Distribute reporting package"]}
    ]
    
    def __init__(self, apiClient):
        """
        Initialize manager with API client.
        
        Args:
            apiClient: D6eApiClient instance
        """
        self.api = apiClient
    
    def initializeCloseTasks(
        self,
        periodName: str,
        periodEndDate: str,
        closeDays: int = 5,
        assignees: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Initialize close tasks for a period.
        
        Args:
            periodName: Period to close (e.g., "2025-01")
            periodEndDate: Last day of the period (YYYY-MM-DD)
            closeDays: Number of business days for close (default: 5)
            assignees: Optional mapping of category to assignee
        
        Returns:
            Initialized close tasks with schedule
        """
        logger.info(f"Initializing close tasks for period: {periodName}")
        
        # Calculate business day dates
        periodEnd = datetime.strptime(periodEndDate, '%Y-%m-%d').date()
        businessDays = self._calculateBusinessDays(periodEnd, closeDays)
        
        tasks = []
        taskIdMap = {}  # Map task name to ID for dependency resolution
        
        for template in self.STANDARD_CLOSE_TASKS:
            if template['day'] > closeDays:
                continue
            
            taskId = str(uuid.uuid4())
            taskIdMap[template['name']] = taskId
            
            dueDate = businessDays.get(template['day'])
            
            # Resolve dependencies to IDs
            dependencyIds = [
                taskIdMap[dep] for dep in template['dependencies'] 
                if dep in taskIdMap
            ]
            
            # Assign based on category
            assignee = None
            if assignees:
                assignee = assignees.get(template['category'])
            
            task = {
                "id": taskId,
                "name": template['name'],
                "category": template['category'],
                "scheduled_day": template['day'],
                "due_date": dueDate.isoformat() if dueDate else None,
                "dependencies": dependencyIds,
                "dependency_names": template['dependencies'],
                "assigned_to": assignee,
                "status": "NOT_STARTED",
                "notes": None,
                "created_at": datetime.now().isoformat()
            }
            
            tasks.append(task)
        
        # Group by day
        tasksByDay = {}
        for task in tasks:
            day = task['scheduled_day']
            if day not in tasksByDay:
                tasksByDay[day] = []
            tasksByDay[day].append(task)
        
        return {
            "period": periodName,
            "period_end_date": periodEndDate,
            "close_days": closeDays,
            "schedule": {
                f"T+{day}": {
                    "date": businessDays.get(day, periodEnd).isoformat() if businessDays.get(day) else None,
                    "tasks": tasksByDay.get(day, [])
                }
                for day in range(1, closeDays + 1)
            },
            "all_tasks": tasks,
            "summary": {
                "total_tasks": len(tasks),
                "tasks_by_category": self._countByCategory(tasks),
                "tasks_by_day": {f"T+{day}": len(tasksByDay.get(day, [])) for day in range(1, closeDays + 1)}
            }
        }
    
    def _calculateBusinessDays(
        self,
        startDate: date,
        numDays: int
    ) -> Dict[int, date]:
        """Calculate business day dates from period end."""
        businessDays = {}
        currentDate = startDate
        dayCount = 0
        
        while dayCount < numDays:
            currentDate = currentDate + timedelta(days=1)
            # Skip weekends (0=Monday, 6=Sunday)
            if currentDate.weekday() < 5:
                dayCount += 1
                businessDays[dayCount] = currentDate
        
        return businessDays
    
    def _countByCategory(self, tasks: List[Dict]) -> Dict[str, int]:
        """Count tasks by category."""
        counts = {}
        for task in tasks:
            category = task.get('category', 'OTHER')
            counts[category] = counts.get(category, 0) + 1
        return counts
    
    def updateTaskStatus(
        self,
        taskId: str,
        newStatus: str,
        notes: Optional[str] = None,
        completedBy: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update status of a close task.
        
        Args:
            taskId: Task ID to update
            newStatus: New status (NOT_STARTED, IN_PROGRESS, COMPLETED, BLOCKED)
            notes: Optional notes
            completedBy: Who completed the task (if applicable)
        
        Returns:
            Updated task information
        """
        logger.info(f"Updating task {taskId} to status: {newStatus}")
        
        validStatuses = ["NOT_STARTED", "IN_PROGRESS", "COMPLETED", "BLOCKED"]
        if newStatus not in validStatuses:
            raise ValueError(f"Invalid status: {newStatus}. Valid: {', '.join(validStatuses)}")
        
        now = datetime.now().isoformat()
        
        update = {
            "task_id": taskId,
            "new_status": newStatus,
            "notes": notes,
            "updated_at": now
        }
        
        if newStatus == "COMPLETED":
            update["completed_at"] = now
            update["completed_by"] = completedBy
        
        # In production, would UPDATE close_tasks table
        
        return update
    
    def getCloseProgress(
        self,
        periodName: str
    ) -> Dict[str, Any]:
        """
        Get overall close progress for a period.
        
        Args:
            periodName: Period to check
        
        Returns:
            Progress summary with metrics
        """
        logger.info(f"Getting close progress for period: {periodName}")
        
        # Query task status
        sql = f"""
            SELECT 
                ct.id,
                ct.task_name,
                ct.task_category,
                ct.scheduled_day,
                ct.status,
                ct.due_date,
                ct.completed_at,
                ct.assigned_to
            FROM close_tasks ct
            JOIN fiscal_periods fp ON ct.fiscal_period_id = fp.id
            WHERE fp.period_name = '{periodName}'
            ORDER BY ct.scheduled_day, ct.task_name
        """
        
        result = self.api.executeSql(sql)
        
        tasks = []
        statusCounts = {"NOT_STARTED": 0, "IN_PROGRESS": 0, "COMPLETED": 0, "BLOCKED": 0}
        lateTasks = []
        today = date.today()
        
        for row in result.get('rows', []):
            status = row[4]
            statusCounts[status] = statusCounts.get(status, 0) + 1
            
            dueDate = datetime.strptime(row[5], '%Y-%m-%d').date() if row[5] else None
            isLate = dueDate and dueDate < today and status not in ("COMPLETED",)
            
            task = {
                "id": row[0],
                "name": row[1],
                "category": row[2],
                "scheduled_day": row[3],
                "status": status,
                "due_date": row[5],
                "completed_at": row[6],
                "assigned_to": row[7],
                "is_late": isLate
            }
            
            tasks.append(task)
            
            if isLate:
                lateTasks.append(task)
        
        totalTasks = len(tasks)
        completedTasks = statusCounts.get("COMPLETED", 0)
        
        return {
            "period": periodName,
            "progress": {
                "total_tasks": totalTasks,
                "completed": completedTasks,
                "in_progress": statusCounts.get("IN_PROGRESS", 0),
                "not_started": statusCounts.get("NOT_STARTED", 0),
                "blocked": statusCounts.get("BLOCKED", 0),
                "completion_percentage": (completedTasks / totalTasks * 100) if totalTasks > 0 else 0
            },
            "status_breakdown": statusCounts,
            "late_tasks": lateTasks,
            "late_task_count": len(lateTasks),
            "tasks": tasks,
            "health": self._assessCloseHealth(statusCounts, lateTasks, totalTasks)
        }
    
    def _assessCloseHealth(
        self,
        statusCounts: Dict,
        lateTasks: List,
        totalTasks: int
    ) -> Dict[str, Any]:
        """Assess overall health of the close."""
        blockedCount = statusCounts.get("BLOCKED", 0)
        lateCount = len(lateTasks)
        completedPct = statusCounts.get("COMPLETED", 0) / totalTasks * 100 if totalTasks > 0 else 0
        
        if blockedCount > 0 or lateCount > 3:
            status = "AT_RISK"
            message = "Close is at risk due to blocked or late tasks"
        elif lateCount > 0 or completedPct < 50:
            status = "NEEDS_ATTENTION"
            message = "Close needs attention - some tasks behind schedule"
        else:
            status = "ON_TRACK"
            message = "Close is on track"
        
        return {
            "status": status,
            "message": message,
            "risk_factors": {
                "blocked_tasks": blockedCount,
                "late_tasks": lateCount,
                "completion_below_target": completedPct < 80
            }
        }
    
    def identifyBlockers(
        self,
        periodName: str
    ) -> Dict[str, Any]:
        """
        Identify blocked tasks and their dependencies.
        
        Args:
            periodName: Period to check
        
        Returns:
            Blocked tasks with blocker analysis
        """
        logger.info(f"Identifying blockers for period: {periodName}")
        
        # Query tasks with their dependencies
        sql = f"""
            SELECT 
                ct.id,
                ct.task_name,
                ct.task_category,
                ct.scheduled_day,
                ct.status,
                ct.dependency_task_ids,
                ct.notes
            FROM close_tasks ct
            JOIN fiscal_periods fp ON ct.fiscal_period_id = fp.id
            WHERE fp.period_name = '{periodName}'
            ORDER BY ct.scheduled_day
        """
        
        result = self.api.executeSql(sql)
        
        allTasks = {}
        blockedTasks = []
        
        # First pass: collect all tasks
        for row in result.get('rows', []):
            taskId = row[0]
            allTasks[taskId] = {
                "id": taskId,
                "name": row[1],
                "category": row[2],
                "scheduled_day": row[3],
                "status": row[4],
                "dependency_ids": row[5] or [],
                "notes": row[6]
            }
        
        # Second pass: identify blockers
        for taskId, task in allTasks.items():
            if task['status'] == 'BLOCKED':
                blockingTasks = []
                for depId in task['dependency_ids']:
                    depTask = allTasks.get(depId)
                    if depTask and depTask['status'] != 'COMPLETED':
                        blockingTasks.append({
                            "id": depId,
                            "name": depTask['name'],
                            "status": depTask['status']
                        })
                
                blockedTasks.append({
                    **task,
                    "blocking_tasks": blockingTasks,
                    "blocker_count": len(blockingTasks)
                })
            
            # Also identify tasks that SHOULD be blocked but aren't marked
            elif task['status'] == 'NOT_STARTED':
                incompleteDepps = []
                for depId in task['dependency_ids']:
                    depTask = allTasks.get(depId)
                    if depTask and depTask['status'] != 'COMPLETED':
                        incompleteDepps.append(depTask['name'])
                
                if incompleteDepps:
                    task['waiting_on'] = incompleteDepps
        
        # Identify critical blockers (blocking multiple tasks)
        blockerCounts = {}
        for task in blockedTasks:
            for blocker in task.get('blocking_tasks', []):
                blockerId = blocker['id']
                blockerCounts[blockerId] = blockerCounts.get(blockerId, 0) + 1
        
        criticalBlockers = [
            {
                "task_id": taskId,
                "task_name": allTasks[taskId]['name'],
                "status": allTasks[taskId]['status'],
                "blocking_count": count
            }
            for taskId, count in blockerCounts.items()
            if count > 1
        ]
        criticalBlockers.sort(key=lambda x: x['blocking_count'], reverse=True)
        
        return {
            "period": periodName,
            "blocked_tasks": blockedTasks,
            "blocked_count": len(blockedTasks),
            "critical_blockers": criticalBlockers,
            "recommendations": self._generateBlockerRecommendations(blockedTasks, criticalBlockers)
        }
    
    def _generateBlockerRecommendations(
        self,
        blockedTasks: List,
        criticalBlockers: List
    ) -> List[str]:
        """Generate recommendations for resolving blockers."""
        recommendations = []
        
        if criticalBlockers:
            top = criticalBlockers[0]
            recommendations.append(
                f"Priority: Complete '{top['task_name']}' - it is blocking {top['blocking_count']} other tasks"
            )
        
        if len(blockedTasks) > 3:
            recommendations.append(
                "Consider parallel processing or additional resources to accelerate blocked tasks"
            )
        
        categories = set(t['category'] for t in blockedTasks)
        if 'RECONCILIATION' in categories:
            recommendations.append(
                "Multiple reconciliation tasks blocked - consider expediting data availability"
            )
        
        if not recommendations:
            recommendations.append("No significant blockers identified")
        
        return recommendations
    
    def generateCloseCalendar(
        self,
        periodName: str,
        periodEndDate: str,
        closeDays: int = 5
    ) -> Dict[str, Any]:
        """
        Generate close calendar with deadlines.
        
        Args:
            periodName: Period for calendar
            periodEndDate: Last day of the period
            closeDays: Number of close days
        
        Returns:
            Close calendar with daily tasks and deadlines
        """
        logger.info(f"Generating close calendar for period: {periodName}")
        
        periodEnd = datetime.strptime(periodEndDate, '%Y-%m-%d').date()
        businessDays = self._calculateBusinessDays(periodEnd, closeDays)
        
        calendar = {
            "period": periodName,
            "period_end_date": periodEndDate,
            "close_start_date": businessDays[1].isoformat(),
            "target_close_date": businessDays[closeDays].isoformat(),
            "days": []
        }
        
        for day in range(1, closeDays + 1):
            dayDate = businessDays[day]
            dayTasks = [t for t in self.STANDARD_CLOSE_TASKS if t['day'] == day]
            
            calendar["days"].append({
                "day": f"T+{day}",
                "date": dayDate.isoformat(),
                "day_of_week": dayDate.strftime('%A'),
                "task_count": len(dayTasks),
                "tasks": [
                    {
                        "name": t['name'],
                        "category": t['category'],
                        "dependencies": t['dependencies']
                    }
                    for t in dayTasks
                ],
                "milestones": self._getDayMilestones(day)
            })
        
        # Generate text calendar
        calendar["text_format"] = self._generateTextCalendar(calendar)
        
        return calendar
    
    def _getDayMilestones(self, day: int) -> List[str]:
        """Get key milestones for each close day."""
        milestones = {
            1: ["All subledgers processed", "Payroll entries posted"],
            2: ["Bank reconciliation complete", "Revenue recognized"],
            3: ["All balance sheet accounts reconciled", "Preliminary TB ready"],
            4: ["Tax provision booked", "Draft financials ready for review"],
            5: ["Hard close complete", "Reporting package distributed"]
        }
        return milestones.get(day, [])
    
    def _generateTextCalendar(self, calendar: Dict) -> str:
        """Generate text-based close calendar."""
        lines = [
            f"CLOSE CALENDAR: {calendar['period']}",
            f"Period End: {calendar['period_end_date']}",
            f"Target Close: {calendar['target_close_date']}",
            "=" * 70,
            ""
        ]
        
        for day in calendar['days']:
            lines.append(f"{day['day']} - {day['date']} ({day['day_of_week']})")
            lines.append("-" * 40)
            
            for task in day['tasks']:
                lines.append(f"  [ ] {task['name']}")
                if task['dependencies']:
                    lines.append(f"      Depends on: {', '.join(task['dependencies'][:2])}")
            
            if day['milestones']:
                lines.append(f"  Milestones: {', '.join(day['milestones'])}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def getCriticalPath(
        self,
        periodName: str
    ) -> Dict[str, Any]:
        """
        Identify critical path tasks that determine minimum close duration.
        
        Args:
            periodName: Period to analyze
        
        Returns:
            Critical path analysis
        """
        logger.info(f"Analyzing critical path for period: {periodName}")
        
        # Build dependency graph
        taskGraph = {}
        for task in self.STANDARD_CLOSE_TASKS:
            taskGraph[task['name']] = {
                "day": task['day'],
                "dependencies": task['dependencies'],
                "category": task['category']
            }
        
        # Find longest path (simplified - uses day as proxy for duration)
        criticalPath = []
        
        # Start from final task and work backwards
        finalTasks = [t for t in self.STANDARD_CLOSE_TASKS if t['day'] == 5]
        
        for finalTask in finalTasks:
            path = self._tracePath(finalTask['name'], taskGraph)
            if len(path) > len(criticalPath):
                criticalPath = path
        
        return {
            "period": periodName,
            "critical_path": criticalPath,
            "path_length": len(criticalPath),
            "minimum_close_days": max(t['day'] for t in self.STANDARD_CLOSE_TASKS),
            "critical_path_tasks": [
                {
                    "sequence": i + 1,
                    "task_name": taskName,
                    "scheduled_day": taskGraph[taskName]['day'],
                    "category": taskGraph[taskName]['category']
                }
                for i, taskName in enumerate(criticalPath)
            ],
            "acceleration_opportunities": [
                "Automate depreciation and amortization entries",
                "Pre-reconcile accounts during the month",
                "Implement continuous close practices",
                "Parallel process independent reconciliations"
            ]
        }
    
    def _tracePath(self, taskName: str, graph: Dict, visited: set = None) -> List[str]:
        """Trace dependency path for a task."""
        if visited is None:
            visited = set()
        
        if taskName in visited:
            return []
        
        visited.add(taskName)
        
        task = graph.get(taskName)
        if not task:
            return [taskName]
        
        longestDepPath = []
        for dep in task['dependencies']:
            depPath = self._tracePath(dep, graph, visited.copy())
            if len(depPath) > len(longestDepPath):
                longestDepPath = depPath
        
        return longestDepPath + [taskName]


def main():
    """Main entry point for the Close Management STF."""
    try:
        inputData = readInput()
        userInput = inputData.get("input", {})
        
        operation = userInput.get("operation")
        if not operation:
            raise ValueError("Missing required field: operation")
        
        apiClient = createApiClient(inputData)
        manager = CloseManager(apiClient)
        
        if operation == "initialize_close_tasks":
            validateRequiredFields(userInput, ["period", "period_end_date"])
            result = manager.initializeCloseTasks(
                periodName=userInput["period"],
                periodEndDate=userInput["period_end_date"],
                closeDays=userInput.get("close_days", 5),
                assignees=userInput.get("assignees")
            )
            
        elif operation == "update_task_status":
            validateRequiredFields(userInput, ["task_id", "new_status"])
            result = manager.updateTaskStatus(
                taskId=userInput["task_id"],
                newStatus=userInput["new_status"],
                notes=userInput.get("notes"),
                completedBy=userInput.get("completed_by")
            )
            
        elif operation == "get_close_progress":
            validateRequiredFields(userInput, ["period"])
            result = manager.getCloseProgress(
                periodName=userInput["period"]
            )
            
        elif operation == "identify_blockers":
            validateRequiredFields(userInput, ["period"])
            result = manager.identifyBlockers(
                periodName=userInput["period"]
            )
            
        elif operation == "generate_close_calendar":
            validateRequiredFields(userInput, ["period", "period_end_date"])
            result = manager.generateCloseCalendar(
                periodName=userInput["period"],
                periodEndDate=userInput["period_end_date"],
                closeDays=userInput.get("close_days", 5)
            )
            
        elif operation == "get_critical_path":
            validateRequiredFields(userInput, ["period"])
            result = manager.getCriticalPath(
                periodName=userInput["period"]
            )
            
        else:
            raise ValueError(
                f"Unknown operation: {operation}. "
                f"Valid operations: initialize_close_tasks, update_task_status, "
                f"get_close_progress, identify_blockers, generate_close_calendar, get_critical_path"
            )
        
        writeOutput({
            "status": "success",
            "operation": operation,
            "data": result
        })
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        writeError(e, "ValidationError")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        writeError(e)


if __name__ == "__main__":
    main()
