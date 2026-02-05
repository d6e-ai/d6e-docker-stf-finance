#!/usr/bin/env python3
"""
D6E Docker STF: Account Reconciliation

Overview:
    Performs account reconciliation tasks including:
    - Bank reconciliation
    - GL to subledger reconciliation
    - Intercompany reconciliation
    - Reconciling item management and aging

Main Operations:
    - create_bank_reconciliation: Reconcile GL to bank statement
    - create_gl_subledger_rec: Reconcile GL to subledger
    - create_intercompany_rec: Reconcile intercompany balances
    - add_reconciling_item: Add reconciling item to a rec
    - analyze_aging: Analyze aging of reconciling items
    - get_reconciliation_status: Get status of reconciliations

Limitations:
    - Bank transaction matching is rule-based, not ML-based
    - Intercompany requires both entities in same workspace
    - Currency conversion not supported
"""

import sys
import os
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

from utils import (
    logger, readInput, writeOutput, writeError,
    createApiClient, validateRequiredFields,
    formatCurrency
)


class ReconciliationManager:
    """
    Manages account reconciliation workflows.
    """
    
    # Age bucket definitions (days)
    AGE_BUCKETS = [
        {"name": "Current (0-30)", "min": 0, "max": 30, "status": "CURRENT"},
        {"name": "Aging (31-60)", "min": 31, "max": 60, "status": "AGING"},
        {"name": "Overdue (61-90)", "min": 61, "max": 90, "status": "OVERDUE"},
        {"name": "Stale (90+)", "min": 91, "max": 9999, "status": "STALE"}
    ]
    
    def __init__(self, apiClient):
        """
        Initialize manager with API client.
        
        Args:
            apiClient: D6eApiClient instance
        """
        self.api = apiClient
    
    def createBankReconciliation(
        self,
        bankAccountId: str,
        periodName: str,
        bankStatementBalance: float,
        bankStatementDate: str
    ) -> Dict[str, Any]:
        """
        Create a bank reconciliation.
        
        Args:
            bankAccountId: GL cash account ID
            periodName: Period for reconciliation
            bankStatementBalance: Balance per bank statement
            bankStatementDate: Date of bank statement
        
        Returns:
            Bank reconciliation with reconciling items
        """
        logger.info(f"Creating bank reconciliation for account: {bankAccountId}")
        
        # Get GL balance
        glSql = f"""
            SELECT 
                a.account_code,
                a.account_name,
                ab.ending_balance
            FROM accounts a
            JOIN account_balances ab ON a.id = ab.account_id
            JOIN fiscal_periods fp ON ab.fiscal_period_id = fp.id
            WHERE a.id = '{bankAccountId}'
            AND fp.period_name = '{periodName}'
        """
        
        glResult = self.api.executeSql(glSql)
        
        if not glResult.get('rows'):
            raise ValueError(f"No balance found for account {bankAccountId} in period {periodName}")
        
        accountCode = glResult['rows'][0][0]
        accountName = glResult['rows'][0][1]
        glBalance = float(glResult['rows'][0][2]) if glResult['rows'][0][2] else 0
        
        # Get outstanding checks (uncleared debits)
        checksSql = f"""
            SELECT 
                jl.reference,
                je.entry_date,
                jl.credit_amount,
                jl.description
            FROM journal_lines jl
            JOIN journal_entries je ON jl.journal_entry_id = je.id
            WHERE jl.account_id = '{bankAccountId}'
            AND jl.credit_amount > 0
            AND je.entry_date <= '{bankStatementDate}'
            AND je.status = 'POSTED'
            ORDER BY je.entry_date
            LIMIT 50
        """
        
        # Note: In production, would track actual cleared status
        # For now, simulate with synthetic data
        
        # Get deposits in transit (uncleared credits)
        depositsSql = f"""
            SELECT 
                jl.reference,
                je.entry_date,
                jl.debit_amount,
                jl.description
            FROM journal_lines jl
            JOIN journal_entries je ON jl.journal_entry_id = je.id
            WHERE jl.account_id = '{bankAccountId}'
            AND jl.debit_amount > 0
            AND je.entry_date <= '{bankStatementDate}'
            AND je.status = 'POSTED'
            ORDER BY je.entry_date DESC
            LIMIT 20
        """
        
        # Build reconciliation structure
        reconciliation = {
            "reconciliation_type": "BANK",
            "account_id": bankAccountId,
            "account_code": accountCode,
            "account_name": accountName,
            "period": periodName,
            "statement_date": bankStatementDate,
            "status": "DRAFT",
            "prepared_at": datetime.now().isoformat(),
            
            "bank_side": {
                "balance_per_bank": bankStatementBalance,
                "adjustments": [],
                "adjusted_balance": bankStatementBalance
            },
            
            "gl_side": {
                "balance_per_gl": glBalance,
                "adjustments": [],
                "adjusted_balance": glBalance
            },
            
            "reconciling_items": {
                "outstanding_checks": [],
                "deposits_in_transit": [],
                "bank_errors": [],
                "gl_errors": [],
                "unrecorded_bank_items": []
            }
        }
        
        # Calculate difference
        difference = bankStatementBalance - glBalance
        
        # If there's a difference, create placeholder reconciling items
        if abs(difference) > 0.01:
            if difference > 0:
                # Bank higher than GL - likely unrecorded deposits or outstanding checks
                reconciliation["reconciling_items"]["deposits_in_transit"].append({
                    "id": str(uuid.uuid4()),
                    "date": bankStatementDate,
                    "description": "Unidentified reconciling item - investigate",
                    "amount": difference,
                    "category": "TIMING",
                    "status": "OPEN",
                    "age_days": 0
                })
            else:
                # GL higher than bank - likely outstanding checks
                reconciliation["reconciling_items"]["outstanding_checks"].append({
                    "id": str(uuid.uuid4()),
                    "date": bankStatementDate,
                    "description": "Unidentified reconciling item - investigate",
                    "amount": abs(difference),
                    "category": "TIMING",
                    "status": "OPEN",
                    "age_days": 0
                })
        
        # Calculate adjusted balances
        totalOutstandingChecks = sum(
            item['amount'] for item in reconciliation["reconciling_items"]["outstanding_checks"]
        )
        totalDepositsInTransit = sum(
            item['amount'] for item in reconciliation["reconciling_items"]["deposits_in_transit"]
        )
        
        reconciliation["bank_side"]["adjustments"] = [
            {"description": "Deposits in transit", "amount": totalDepositsInTransit},
            {"description": "Outstanding checks", "amount": -totalOutstandingChecks}
        ]
        reconciliation["bank_side"]["adjusted_balance"] = (
            bankStatementBalance + totalDepositsInTransit - totalOutstandingChecks
        )
        
        reconciliation["gl_side"]["adjusted_balance"] = glBalance
        
        # Validation
        finalDifference = (
            reconciliation["bank_side"]["adjusted_balance"] - 
            reconciliation["gl_side"]["adjusted_balance"]
        )
        
        reconciliation["validation"] = {
            "difference": finalDifference,
            "is_reconciled": abs(finalDifference) < 0.01,
            "total_reconciling_items": (
                len(reconciliation["reconciling_items"]["outstanding_checks"]) +
                len(reconciliation["reconciling_items"]["deposits_in_transit"]) +
                len(reconciliation["reconciling_items"]["bank_errors"]) +
                len(reconciliation["reconciling_items"]["gl_errors"])
            )
        }
        
        # Standard format output
        reconciliation["text_format"] = self._generateBankRecTextFormat(reconciliation)
        
        return reconciliation
    
    def _generateBankRecTextFormat(self, rec: Dict) -> str:
        """Generate standard bank reconciliation format."""
        lines = [
            f"BANK RECONCILIATION - {rec['account_name']} ({rec['account_code']})",
            f"Period: {rec['period']}  Statement Date: {rec['statement_date']}",
            "=" * 60,
            "",
            f"Balance per bank statement:         {formatCurrency(rec['bank_side']['balance_per_bank']):>15}",
        ]
        
        for adj in rec['bank_side']['adjustments']:
            prefix = "Add:" if adj['amount'] > 0 else "Less:"
            lines.append(f"  {prefix} {adj['description']:<30} {formatCurrency(adj['amount']):>15}")
        
        lines.append(f"Adjusted bank balance:              {formatCurrency(rec['bank_side']['adjusted_balance']):>15}")
        lines.append("")
        lines.append(f"Balance per general ledger:         {formatCurrency(rec['gl_side']['balance_per_gl']):>15}")
        
        for adj in rec['gl_side'].get('adjustments', []):
            prefix = "Add:" if adj['amount'] > 0 else "Less:"
            lines.append(f"  {prefix} {adj['description']:<30} {formatCurrency(adj['amount']):>15}")
        
        lines.append(f"Adjusted GL balance:                {formatCurrency(rec['gl_side']['adjusted_balance']):>15}")
        lines.append("")
        lines.append("-" * 60)
        lines.append(f"Difference:                         {formatCurrency(rec['validation']['difference']):>15}")
        lines.append(f"Status: {'RECONCILED' if rec['validation']['is_reconciled'] else 'UNRECONCILED'}")
        
        return "\n".join(lines)
    
    def createGlSubledgerRec(
        self,
        controlAccountId: str,
        periodName: str,
        subledgerBalance: float,
        subledgerSource: str
    ) -> Dict[str, Any]:
        """
        Create GL to subledger reconciliation.
        
        Args:
            controlAccountId: GL control account ID
            periodName: Period for reconciliation
            subledgerBalance: Balance per subledger
            subledgerSource: Source system name (e.g., "AR_AGING", "AP_AGING")
        
        Returns:
            GL-Subledger reconciliation
        """
        logger.info(f"Creating GL-SL reconciliation for account: {controlAccountId}")
        
        # Get GL balance
        glSql = f"""
            SELECT 
                a.account_code,
                a.account_name,
                coa.account_category,
                ab.ending_balance
            FROM accounts a
            JOIN chart_of_accounts coa ON a.chart_of_accounts_id = coa.id
            JOIN account_balances ab ON a.id = ab.account_id
            JOIN fiscal_periods fp ON ab.fiscal_period_id = fp.id
            WHERE a.id = '{controlAccountId}'
            AND fp.period_name = '{periodName}'
        """
        
        glResult = self.api.executeSql(glSql)
        
        if not glResult.get('rows'):
            raise ValueError(f"No balance found for account {controlAccountId} in period {periodName}")
        
        accountCode = glResult['rows'][0][0]
        accountName = glResult['rows'][0][1]
        accountCategory = glResult['rows'][0][2]
        glBalance = float(glResult['rows'][0][3]) if glResult['rows'][0][3] else 0
        
        difference = glBalance - subledgerBalance
        
        reconciliation = {
            "reconciliation_type": "GL_SUBLEDGER",
            "account_id": controlAccountId,
            "account_code": accountCode,
            "account_name": accountName,
            "account_category": accountCategory,
            "period": periodName,
            "subledger_source": subledgerSource,
            "status": "DRAFT",
            "prepared_at": datetime.now().isoformat(),
            
            "gl_balance": glBalance,
            "subledger_balance": subledgerBalance,
            "difference": difference,
            
            "reconciling_items": [],
            
            "validation": {
                "is_reconciled": abs(difference) < 0.01,
                "difference": difference
            }
        }
        
        # Add reconciling item for any difference
        if abs(difference) > 0.01:
            reconciliation["reconciling_items"].append({
                "id": str(uuid.uuid4()),
                "date": datetime.now().strftime('%Y-%m-%d'),
                "description": "Unidentified difference - requires investigation",
                "amount": difference,
                "category": "INVESTIGATION",
                "status": "OPEN",
                "possible_causes": [
                    "Manual journal entries to control account",
                    "Subledger transactions pending interface",
                    "Timing differences in batch posting",
                    "System interface errors"
                ]
            })
        
        return reconciliation
    
    def createIntercompanyRec(
        self,
        entityAAccountId: str,
        entityBAccountId: str,
        periodName: str
    ) -> Dict[str, Any]:
        """
        Create intercompany reconciliation between two entities.
        
        Args:
            entityAAccountId: IC receivable/payable account for Entity A
            entityBAccountId: IC receivable/payable account for Entity B
            periodName: Period for reconciliation
        
        Returns:
            Intercompany reconciliation
        """
        logger.info(f"Creating intercompany reconciliation")
        
        # Get both entity balances
        sql = f"""
            SELECT 
                a.id,
                a.account_code,
                a.account_name,
                ab.ending_balance
            FROM accounts a
            JOIN account_balances ab ON a.id = ab.account_id
            JOIN fiscal_periods fp ON ab.fiscal_period_id = fp.id
            WHERE a.id IN ('{entityAAccountId}', '{entityBAccountId}')
            AND fp.period_name = '{periodName}'
        """
        
        result = self.api.executeSql(sql)
        
        balances = {}
        for row in result.get('rows', []):
            balances[row[0]] = {
                "account_code": row[1],
                "account_name": row[2],
                "balance": float(row[3]) if row[3] else 0
            }
        
        if entityAAccountId not in balances or entityBAccountId not in balances:
            raise ValueError("One or both intercompany accounts not found")
        
        entityA = balances[entityAAccountId]
        entityB = balances[entityBAccountId]
        
        # IC balances should net to zero (one receivable, one payable)
        # A's receivable should equal B's payable (opposite signs)
        netBalance = entityA['balance'] + entityB['balance']
        
        reconciliation = {
            "reconciliation_type": "INTERCOMPANY",
            "period": periodName,
            "status": "DRAFT",
            "prepared_at": datetime.now().isoformat(),
            
            "entity_a": {
                "account_id": entityAAccountId,
                "account_code": entityA['account_code'],
                "account_name": entityA['account_name'],
                "balance": entityA['balance']
            },
            "entity_b": {
                "account_id": entityBAccountId,
                "account_code": entityB['account_code'],
                "account_name": entityB['account_name'],
                "balance": entityB['balance']
            },
            
            "net_balance": netBalance,
            "reconciling_items": [],
            
            "validation": {
                "is_reconciled": abs(netBalance) < 0.01,
                "difference": netBalance,
                "expected_net": 0
            }
        }
        
        if abs(netBalance) > 0.01:
            reconciliation["reconciling_items"].append({
                "id": str(uuid.uuid4()),
                "date": datetime.now().strftime('%Y-%m-%d'),
                "description": "Intercompany out of balance",
                "amount": netBalance,
                "category": "INVESTIGATION",
                "status": "OPEN",
                "possible_causes": [
                    "Transaction recorded by one entity but not the other",
                    "Different FX rates used by each entity",
                    "Misclassification (intercompany vs third-party)",
                    "Timing differences in period-end cut-off"
                ]
            })
        
        return reconciliation
    
    def addReconcilingItem(
        self,
        reconciliationId: str,
        itemDate: str,
        description: str,
        amount: float,
        category: str,
        reference: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a reconciling item to an existing reconciliation.
        
        Args:
            reconciliationId: Reconciliation ID
            itemDate: Date of the reconciling item
            description: Description of the item
            amount: Amount (signed)
            category: TIMING, ADJUSTMENT_REQUIRED, INVESTIGATION
            reference: Optional reference (check#, invoice#)
            notes: Optional notes
        
        Returns:
            Created reconciling item
        """
        logger.info(f"Adding reconciling item to reconciliation: {reconciliationId}")
        
        # Calculate age
        itemDateObj = datetime.strptime(itemDate, '%Y-%m-%d').date()
        today = date.today()
        ageDays = (today - itemDateObj).days
        
        # Determine age bucket
        ageBucket = "Current"
        for bucket in self.AGE_BUCKETS:
            if bucket['min'] <= ageDays <= bucket['max']:
                ageBucket = bucket['name']
                break
        
        item = {
            "id": str(uuid.uuid4()),
            "reconciliation_id": reconciliationId,
            "date": itemDate,
            "description": description,
            "amount": amount,
            "category": category,
            "status": "OPEN",
            "reference": reference,
            "notes": notes,
            "age_days": ageDays,
            "age_bucket": ageBucket,
            "created_at": datetime.now().isoformat()
        }
        
        # In production, would INSERT into reconciling_items table
        
        return item
    
    def analyzeAging(
        self,
        accountId: Optional[str] = None,
        periodName: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze aging of reconciling items.
        
        Args:
            accountId: Optional filter by account
            periodName: Optional filter by period
        
        Returns:
            Aging analysis with buckets and trends
        """
        logger.info("Analyzing reconciling items aging")
        
        # Query reconciling items
        filters = []
        if accountId:
            filters.append(f"r.account_id = '{accountId}'")
        if periodName:
            filters.append(f"fp.period_name = '{periodName}'")
        
        whereClause = f"WHERE {' AND '.join(filters)}" if filters else ""
        
        sql = f"""
            SELECT 
                ri.id,
                ri.item_date,
                ri.description,
                ri.amount,
                ri.category,
                ri.status,
                ri.reference,
                r.account_id,
                a.account_code,
                a.account_name,
                fp.period_name
            FROM reconciling_items ri
            JOIN reconciliations r ON ri.reconciliation_id = r.id
            JOIN accounts a ON r.account_id = a.id
            JOIN fiscal_periods fp ON r.fiscal_period_id = fp.id
            {whereClause}
            AND ri.status = 'OPEN'
            ORDER BY ri.item_date
        """
        
        result = self.api.executeSql(sql)
        
        # Initialize buckets
        buckets = {bucket['name']: {"items": [], "total": 0, "count": 0} 
                   for bucket in self.AGE_BUCKETS}
        
        today = date.today()
        allItems = []
        
        for row in result.get('rows', []):
            itemDate = datetime.strptime(row[1], '%Y-%m-%d').date() if row[1] else today
            ageDays = (today - itemDate).days
            
            item = {
                "id": row[0],
                "date": row[1],
                "description": row[2],
                "amount": float(row[3]) if row[3] else 0,
                "category": row[4],
                "status": row[5],
                "reference": row[6],
                "account_code": row[8],
                "account_name": row[9],
                "period": row[10],
                "age_days": ageDays
            }
            
            # Assign to bucket
            for bucket in self.AGE_BUCKETS:
                if bucket['min'] <= ageDays <= bucket['max']:
                    buckets[bucket['name']]["items"].append(item)
                    buckets[bucket['name']]["total"] += item['amount']
                    buckets[bucket['name']]["count"] += 1
                    item["age_bucket"] = bucket['name']
                    break
            
            allItems.append(item)
        
        # Calculate summary
        totalAmount = sum(bucket['total'] for bucket in buckets.values())
        totalCount = sum(bucket['count'] for bucket in buckets.values())
        
        # Identify items requiring escalation
        escalationItems = [
            item for item in allItems 
            if item['age_days'] > 60 or abs(item['amount']) > 50000
        ]
        
        return {
            "analysis_date": today.isoformat(),
            "filters": {
                "account_id": accountId,
                "period": periodName
            },
            "summary": {
                "total_items": totalCount,
                "total_amount": totalAmount,
                "items_requiring_escalation": len(escalationItems)
            },
            "age_buckets": [
                {
                    "bucket": bucket['name'],
                    "status": bucket['status'],
                    "count": buckets[bucket['name']]['count'],
                    "total": buckets[bucket['name']]['total'],
                    "percentage_of_total": (
                        buckets[bucket['name']]['total'] / totalAmount 
                        if totalAmount != 0 else 0
                    )
                }
                for bucket in self.AGE_BUCKETS
            ],
            "escalation_items": escalationItems[:10],  # Top 10
            "all_items": allItems
        }
    
    def getReconciliationStatus(
        self,
        periodName: str,
        reconciliationType: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get status of all reconciliations for a period.
        
        Args:
            periodName: Period to check
            reconciliationType: Optional filter (BANK, GL_SUBLEDGER, INTERCOMPANY)
        
        Returns:
            Status summary of all reconciliations
        """
        logger.info(f"Getting reconciliation status for period: {periodName}")
        
        typeFilter = f"AND r.reconciliation_type = '{reconciliationType}'" if reconciliationType else ""
        
        sql = f"""
            SELECT 
                r.id,
                a.account_code,
                a.account_name,
                r.reconciliation_type,
                r.status,
                r.gl_balance,
                r.external_balance,
                r.reconciling_items_total,
                r.prepared_by,
                r.approved_by,
                r.completed_at,
                (SELECT COUNT(*) FROM reconciling_items ri WHERE ri.reconciliation_id = r.id AND ri.status = 'OPEN') as open_items
            FROM reconciliations r
            JOIN accounts a ON r.account_id = a.id
            JOIN fiscal_periods fp ON r.fiscal_period_id = fp.id
            WHERE fp.period_name = '{periodName}'
            {typeFilter}
            ORDER BY r.reconciliation_type, a.account_code
        """
        
        result = self.api.executeSql(sql)
        
        reconciliations = []
        statusCounts = {"DRAFT": 0, "IN_PROGRESS": 0, "COMPLETED": 0, "APPROVED": 0}
        
        for row in result.get('rows', []):
            status = row[4]
            statusCounts[status] = statusCounts.get(status, 0) + 1
            
            reconciliations.append({
                "id": row[0],
                "account_code": row[1],
                "account_name": row[2],
                "reconciliation_type": row[3],
                "status": status,
                "gl_balance": float(row[5]) if row[5] else 0,
                "external_balance": float(row[6]) if row[6] else 0,
                "reconciling_items_total": float(row[7]) if row[7] else 0,
                "prepared_by": row[8],
                "approved_by": row[9],
                "completed_at": row[10],
                "open_items_count": row[11] or 0
            })
        
        totalRecs = len(reconciliations)
        
        return {
            "period": periodName,
            "reconciliation_type_filter": reconciliationType,
            "summary": {
                "total_reconciliations": totalRecs,
                "completed_count": statusCounts.get("COMPLETED", 0) + statusCounts.get("APPROVED", 0),
                "pending_count": statusCounts.get("DRAFT", 0) + statusCounts.get("IN_PROGRESS", 0),
                "completion_percentage": (
                    (statusCounts.get("COMPLETED", 0) + statusCounts.get("APPROVED", 0)) / totalRecs * 100
                    if totalRecs > 0 else 0
                )
            },
            "status_breakdown": statusCounts,
            "reconciliations": reconciliations,
            "action_items": [
                rec for rec in reconciliations 
                if rec['status'] in ('DRAFT', 'IN_PROGRESS') or rec['open_items_count'] > 0
            ]
        }


def main():
    """Main entry point for the Reconciliation STF."""
    try:
        inputData = readInput()
        userInput = inputData.get("input", {})
        
        operation = userInput.get("operation")
        if not operation:
            raise ValueError("Missing required field: operation")
        
        apiClient = createApiClient(inputData)
        manager = ReconciliationManager(apiClient)
        
        if operation == "create_bank_reconciliation":
            validateRequiredFields(userInput, [
                "bank_account_id", "period", "bank_statement_balance", "bank_statement_date"
            ])
            result = manager.createBankReconciliation(
                bankAccountId=userInput["bank_account_id"],
                periodName=userInput["period"],
                bankStatementBalance=float(userInput["bank_statement_balance"]),
                bankStatementDate=userInput["bank_statement_date"]
            )
            
        elif operation == "create_gl_subledger_rec":
            validateRequiredFields(userInput, [
                "control_account_id", "period", "subledger_balance", "subledger_source"
            ])
            result = manager.createGlSubledgerRec(
                controlAccountId=userInput["control_account_id"],
                periodName=userInput["period"],
                subledgerBalance=float(userInput["subledger_balance"]),
                subledgerSource=userInput["subledger_source"]
            )
            
        elif operation == "create_intercompany_rec":
            validateRequiredFields(userInput, [
                "entity_a_account_id", "entity_b_account_id", "period"
            ])
            result = manager.createIntercompanyRec(
                entityAAccountId=userInput["entity_a_account_id"],
                entityBAccountId=userInput["entity_b_account_id"],
                periodName=userInput["period"]
            )
            
        elif operation == "add_reconciling_item":
            validateRequiredFields(userInput, [
                "reconciliation_id", "item_date", "description", "amount", "category"
            ])
            result = manager.addReconcilingItem(
                reconciliationId=userInput["reconciliation_id"],
                itemDate=userInput["item_date"],
                description=userInput["description"],
                amount=float(userInput["amount"]),
                category=userInput["category"],
                reference=userInput.get("reference"),
                notes=userInput.get("notes")
            )
            
        elif operation == "analyze_aging":
            result = manager.analyzeAging(
                accountId=userInput.get("account_id"),
                periodName=userInput.get("period")
            )
            
        elif operation == "get_reconciliation_status":
            validateRequiredFields(userInput, ["period"])
            result = manager.getReconciliationStatus(
                periodName=userInput["period"],
                reconciliationType=userInput.get("reconciliation_type")
            )
            
        else:
            raise ValueError(
                f"Unknown operation: {operation}. "
                f"Valid operations: create_bank_reconciliation, create_gl_subledger_rec, "
                f"create_intercompany_rec, add_reconciling_item, analyze_aging, get_reconciliation_status"
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
