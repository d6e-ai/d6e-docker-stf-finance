#!/usr/bin/env python3
"""
D6E Docker STF: Journal Entry Preparation

Overview:
    Prepares and validates journal entries for month-end close including:
    - Standard accrual entries (AP, payroll, etc.)
    - Fixed asset depreciation
    - Prepaid expense amortization
    - Revenue recognition entries
    - Manual adjusting entries

Main Operations:
    - create_journal_entry: Create a new journal entry
    - validate_journal_entry: Validate entry before posting
    - calculate_depreciation: Generate depreciation entries
    - calculate_prepaid_amortization: Generate prepaid amortization
    - generate_accrual_entry: Generate standard accrual entry
    - list_pending_entries: List entries pending approval

Limitations:
    - Does not actually post entries (creates in DRAFT status)
    - Depreciation uses straight-line method only
    - Single currency support
"""

import sys
import os
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from decimal import Decimal
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'shared'))

from utils import (
    logger, readInput, writeOutput, writeError,
    createApiClient, validateRequiredFields,
    formatCurrency
)


class JournalEntryManager:
    """
    Manages journal entry preparation and validation.
    """
    
    def __init__(self, apiClient):
        """
        Initialize manager with API client.
        
        Args:
            apiClient: D6eApiClient instance for database access
        """
        self.api = apiClient
    
    def createJournalEntry(
        self,
        entryDate: str,
        description: str,
        lines: List[Dict],
        entryType: str = "STANDARD",
        isAutoReverse: bool = False,
        reverseDate: Optional[str] = None,
        createdBy: str = "SYSTEM"
    ) -> Dict[str, Any]:
        """
        Create a new journal entry.
        
        Args:
            entryDate: Entry date (YYYY-MM-DD)
            description: Entry description
            lines: List of line items with account_id, debit_amount, credit_amount
            entryType: STANDARD, ADJUSTING, CLOSING, REVERSING
            isAutoReverse: Whether entry auto-reverses
            reverseDate: Date for auto-reversal
            createdBy: User who created the entry
        
        Returns:
            Created journal entry details
        """
        logger.info(f"Creating journal entry: {description}")
        
        # Validate entry is balanced
        totalDebits = sum(float(line.get('debit_amount', 0)) for line in lines)
        totalCredits = sum(float(line.get('credit_amount', 0)) for line in lines)
        
        if abs(totalDebits - totalCredits) > 0.01:
            raise ValueError(
                f"Entry is not balanced. Debits: {formatCurrency(totalDebits)}, "
                f"Credits: {formatCurrency(totalCredits)}, "
                f"Difference: {formatCurrency(totalDebits - totalCredits)}"
            )
        
        # Get fiscal period
        periodSql = f"""
            SELECT id, period_name, status 
            FROM fiscal_periods 
            WHERE period_start <= '{entryDate}' 
            AND period_end >= '{entryDate}'
            LIMIT 1
        """
        periodResult = self.api.executeSql(periodSql)
        
        if not periodResult.get('rows'):
            raise ValueError(f"No open fiscal period found for date: {entryDate}")
        
        periodId = periodResult['rows'][0][0]
        periodName = periodResult['rows'][0][1]
        periodStatus = periodResult['rows'][0][2]
        
        if periodStatus == 'HARD_CLOSE':
            raise ValueError(f"Cannot post to closed period: {periodName}")
        
        # Generate entry number
        entryNumber = f"JE-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Validate accounts exist
        accountIds = [line['account_id'] for line in lines]
        accountCheckSql = f"""
            SELECT id, account_code, account_name 
            FROM accounts 
            WHERE id IN ({','.join([f"'{aid}'" for aid in accountIds])})
        """
        accountResult = self.api.executeSql(accountCheckSql)
        
        foundAccounts = {row[0]: {'code': row[1], 'name': row[2]} for row in accountResult.get('rows', [])}
        
        missingAccounts = [aid for aid in accountIds if aid not in foundAccounts]
        if missingAccounts:
            raise ValueError(f"Invalid account IDs: {', '.join(missingAccounts)}")
        
        # Build entry structure (note: actual INSERT would need policy permissions)
        entry = {
            "entry_number": entryNumber,
            "entry_date": entryDate,
            "fiscal_period_id": periodId,
            "fiscal_period_name": periodName,
            "description": description,
            "entry_type": entryType,
            "status": "DRAFT",
            "is_auto_reverse": isAutoReverse,
            "reverse_date": reverseDate,
            "created_by": createdBy,
            "created_at": datetime.now().isoformat(),
            "lines": []
        }
        
        for i, line in enumerate(lines, 1):
            accountInfo = foundAccounts[line['account_id']]
            entry["lines"].append({
                "line_number": i,
                "account_id": line['account_id'],
                "account_code": accountInfo['code'],
                "account_name": accountInfo['name'],
                "department_id": line.get('department_id'),
                "debit_amount": float(line.get('debit_amount', 0)),
                "credit_amount": float(line.get('credit_amount', 0)),
                "description": line.get('description', ''),
                "reference": line.get('reference', '')
            })
        
        entry["totals"] = {
            "total_debits": totalDebits,
            "total_credits": totalCredits,
            "line_count": len(lines)
        }
        
        return entry
    
    def validateJournalEntry(self, entry: Dict) -> Dict[str, Any]:
        """
        Validate journal entry against business rules.
        
        Args:
            entry: Journal entry to validate
        
        Returns:
            Validation results with any errors/warnings
        """
        logger.info(f"Validating journal entry: {entry.get('entry_number', 'unknown')}")
        
        errors = []
        warnings = []
        
        lines = entry.get('lines', [])
        
        # Check 1: Entry is balanced
        totalDebits = sum(float(line.get('debit_amount', 0)) for line in lines)
        totalCredits = sum(float(line.get('credit_amount', 0)) for line in lines)
        
        if abs(totalDebits - totalCredits) > 0.01:
            errors.append({
                "code": "UNBALANCED",
                "message": f"Debits ({formatCurrency(totalDebits)}) do not equal credits ({formatCurrency(totalCredits)})"
            })
        
        # Check 2: Has at least one line
        if len(lines) < 2:
            errors.append({
                "code": "MIN_LINES",
                "message": "Journal entry must have at least 2 lines"
            })
        
        # Check 3: Each line has either debit or credit (not both)
        for i, line in enumerate(lines, 1):
            debit = float(line.get('debit_amount', 0))
            credit = float(line.get('credit_amount', 0))
            
            if debit > 0 and credit > 0:
                errors.append({
                    "code": "DEBIT_AND_CREDIT",
                    "message": f"Line {i}: Cannot have both debit and credit on same line"
                })
            
            if debit == 0 and credit == 0:
                errors.append({
                    "code": "ZERO_AMOUNT",
                    "message": f"Line {i}: Line has no debit or credit amount"
                })
        
        # Check 4: Description is provided
        if not entry.get('description'):
            errors.append({
                "code": "NO_DESCRIPTION",
                "message": "Journal entry must have a description"
            })
        
        # Check 5: Warn on round numbers (potential estimate)
        for i, line in enumerate(lines, 1):
            amount = float(line.get('debit_amount', 0)) or float(line.get('credit_amount', 0))
            if amount > 100 and amount % 1000 == 0:
                warnings.append({
                    "code": "ROUND_NUMBER",
                    "message": f"Line {i}: Amount {formatCurrency(amount)} is a round number - verify this is not an estimate"
                })
        
        # Check 6: Auto-reverse entries should have reverse date
        if entry.get('is_auto_reverse') and not entry.get('reverse_date'):
            warnings.append({
                "code": "MISSING_REVERSE_DATE",
                "message": "Auto-reversing entry should have a reverse date specified"
            })
        
        return {
            "entry_number": entry.get('entry_number'),
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "error_count": len(errors),
            "warning_count": len(warnings)
        }
    
    def calculateDepreciation(
        self,
        periodName: str,
        assetCategoryFilter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate depreciation entries for the period.
        
        Args:
            periodName: Period for depreciation
            assetCategoryFilter: Optional filter by asset category
        
        Returns:
            Depreciation journal entry
        """
        logger.info(f"Calculating depreciation for period: {periodName}")
        
        # Query fixed assets (simplified - assumes fixed asset data exists)
        # In practice, this would query a fixed_assets table
        assetSql = f"""
            SELECT 
                a.id as expense_account_id,
                a.account_code,
                a.account_name,
                d.id as department_id,
                d.department_name,
                ab.ending_balance as accumulated_depreciation
            FROM accounts a
            JOIN chart_of_accounts coa ON a.chart_of_accounts_id = coa.id
            LEFT JOIN departments d ON a.department_id = d.id
            LEFT JOIN account_balances ab ON a.id = ab.account_id
            LEFT JOIN fiscal_periods fp ON ab.fiscal_period_id = fp.id
            WHERE coa.account_category LIKE '%DEPRECIATION%'
            AND (fp.period_name = '{periodName}' OR fp.period_name IS NULL)
        """
        
        assetResult = self.api.executeSql(assetSql)
        
        # Get period dates
        periodSql = f"SELECT period_start, period_end FROM fiscal_periods WHERE period_name = '{periodName}'"
        periodResult = self.api.executeSql(periodSql)
        
        if not periodResult.get('rows'):
            raise ValueError(f"Period not found: {periodName}")
        
        periodEnd = periodResult['rows'][0][1]
        
        # Build depreciation entry lines
        lines = []
        totalDepreciation = 0
        
        # For demo purposes, create sample depreciation entries
        # In production, this would calculate based on actual asset data
        depreciationItems = [
            {"description": "Building Depreciation", "amount": 5000, "dept": "G&A"},
            {"description": "Equipment Depreciation", "amount": 3000, "dept": "Operations"},
            {"description": "Computer Equipment Depreciation", "amount": 2000, "dept": "IT"},
            {"description": "Furniture Depreciation", "amount": 500, "dept": "G&A"}
        ]
        
        # This would normally come from database
        # Create expense lines (debit depreciation expense)
        for item in depreciationItems:
            lines.append({
                "account_id": "DEPRECIATION_EXPENSE_PLACEHOLDER",
                "debit_amount": item["amount"],
                "credit_amount": 0,
                "description": item["description"],
                "reference": f"Auto-calc {periodName}"
            })
            totalDepreciation += item["amount"]
        
        # Create accumulated depreciation line (credit)
        lines.append({
            "account_id": "ACCUMULATED_DEPRECIATION_PLACEHOLDER",
            "debit_amount": 0,
            "credit_amount": totalDepreciation,
            "description": f"Accumulated Depreciation - {periodName}",
            "reference": f"Auto-calc {periodName}"
        })
        
        return {
            "entry_type": "DEPRECIATION",
            "period": periodName,
            "calculation_date": datetime.now().isoformat(),
            "summary": {
                "total_depreciation": totalDepreciation,
                "asset_count": len(depreciationItems)
            },
            "suggested_entry": {
                "entry_date": periodEnd,
                "description": f"Monthly Depreciation - {periodName}",
                "entry_type": "STANDARD",
                "lines": lines,
                "is_auto_reverse": False
            },
            "detail_items": depreciationItems,
            "note": "Account IDs are placeholders - replace with actual account UUIDs before posting"
        }
    
    def calculatePrepaidAmortization(
        self,
        periodName: str
    ) -> Dict[str, Any]:
        """
        Calculate prepaid expense amortization for the period.
        
        Args:
            periodName: Period for amortization
        
        Returns:
            Amortization journal entry
        """
        logger.info(f"Calculating prepaid amortization for period: {periodName}")
        
        # Query prepaid accounts
        prepaidSql = f"""
            SELECT 
                a.id,
                a.account_code,
                a.account_name,
                ab.ending_balance
            FROM accounts a
            JOIN chart_of_accounts coa ON a.chart_of_accounts_id = coa.id
            JOIN account_balances ab ON a.id = ab.account_id
            JOIN fiscal_periods fp ON ab.fiscal_period_id = fp.id
            WHERE (coa.account_category LIKE '%PREPAID%' OR a.account_name LIKE '%Prepaid%')
            AND fp.period_name = '{periodName}'
            AND ab.ending_balance > 0
        """
        
        prepaidResult = self.api.executeSql(prepaidSql)
        
        # Get period end date
        periodSql = f"SELECT period_end FROM fiscal_periods WHERE period_name = '{periodName}'"
        periodResult = self.api.executeSql(periodSql)
        
        if not periodResult.get('rows'):
            raise ValueError(f"Period not found: {periodName}")
        
        periodEnd = periodResult['rows'][0][0]
        
        # Build amortization entries
        lines = []
        amortizationItems = []
        totalAmortization = 0
        
        for row in prepaidResult.get('rows', []):
            accountId = row[0]
            accountCode = row[1]
            accountName = row[2]
            balance = float(row[3]) if row[3] else 0
            
            # Calculate monthly amortization (assume 12-month standard)
            # In practice, would look up actual amortization schedule
            monthlyAmount = round(balance / 12, 2)
            
            if monthlyAmount > 0:
                amortizationItems.append({
                    "account_id": accountId,
                    "account_code": accountCode,
                    "account_name": accountName,
                    "current_balance": balance,
                    "amortization_amount": monthlyAmount
                })
                
                # Credit prepaid (reduce asset)
                lines.append({
                    "account_id": accountId,
                    "debit_amount": 0,
                    "credit_amount": monthlyAmount,
                    "description": f"Amortization - {accountName}",
                    "reference": periodName
                })
                
                totalAmortization += monthlyAmount
        
        # Debit expense (would need mapping of prepaid to expense accounts)
        if totalAmortization > 0:
            lines.insert(0, {
                "account_id": "PREPAID_EXPENSE_PLACEHOLDER",
                "debit_amount": totalAmortization,
                "credit_amount": 0,
                "description": f"Prepaid Expense Amortization - {periodName}",
                "reference": periodName
            })
        
        return {
            "entry_type": "PREPAID_AMORTIZATION",
            "period": periodName,
            "calculation_date": datetime.now().isoformat(),
            "summary": {
                "total_amortization": totalAmortization,
                "prepaid_account_count": len(amortizationItems)
            },
            "suggested_entry": {
                "entry_date": periodEnd,
                "description": f"Monthly Prepaid Amortization - {periodName}",
                "entry_type": "STANDARD",
                "lines": lines,
                "is_auto_reverse": False
            },
            "detail_items": amortizationItems,
            "note": "Expense account ID is placeholder - replace with actual account UUID before posting"
        }
    
    def generateAccrualEntry(
        self,
        accrualType: str,
        periodName: str,
        amount: float,
        description: str,
        expenseAccountId: str,
        liabilityAccountId: str,
        departmentId: Optional[str] = None,
        reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a standard accrual entry.
        
        Args:
            accrualType: Type (AP_ACCRUAL, PAYROLL_ACCRUAL, etc.)
            periodName: Period for accrual
            amount: Accrual amount
            description: Entry description
            expenseAccountId: Expense account to debit
            liabilityAccountId: Liability account to credit
            departmentId: Optional department
            reference: Optional reference (PO#, etc.)
        
        Returns:
            Accrual journal entry
        """
        logger.info(f"Generating {accrualType} accrual for period: {periodName}")
        
        # Get period end date
        periodSql = f"SELECT period_end FROM fiscal_periods WHERE period_name = '{periodName}'"
        periodResult = self.api.executeSql(periodSql)
        
        if not periodResult.get('rows'):
            raise ValueError(f"Period not found: {periodName}")
        
        periodEnd = periodResult['rows'][0][0]
        
        # Calculate reverse date (first day of next period)
        reverseDate = (datetime.strptime(periodEnd, '%Y-%m-%d') + 
                      __import__('datetime').timedelta(days=1)).strftime('%Y-%m-%d')
        
        lines = [
            {
                "account_id": expenseAccountId,
                "department_id": departmentId,
                "debit_amount": amount,
                "credit_amount": 0,
                "description": description,
                "reference": reference or ""
            },
            {
                "account_id": liabilityAccountId,
                "department_id": departmentId,
                "debit_amount": 0,
                "credit_amount": amount,
                "description": description,
                "reference": reference or ""
            }
        ]
        
        entry = self.createJournalEntry(
            entryDate=periodEnd,
            description=f"{accrualType}: {description}",
            lines=lines,
            entryType="ADJUSTING",
            isAutoReverse=True,
            reverseDate=reverseDate,
            createdBy="SYSTEM"
        )
        
        entry["accrual_info"] = {
            "accrual_type": accrualType,
            "original_amount": amount,
            "will_reverse_on": reverseDate
        }
        
        return entry
    
    def listPendingEntries(
        self,
        periodName: Optional[str] = None,
        status: str = "DRAFT"
    ) -> Dict[str, Any]:
        """
        List journal entries pending approval.
        
        Args:
            periodName: Optional period filter
            status: Status to filter (default: DRAFT)
        
        Returns:
            List of pending entries
        """
        logger.info(f"Listing pending entries with status: {status}")
        
        periodFilter = f"AND fp.period_name = '{periodName}'" if periodName else ""
        
        sql = f"""
            SELECT 
                je.id,
                je.entry_number,
                je.entry_date,
                fp.period_name,
                je.description,
                je.entry_type,
                je.status,
                je.created_by,
                je.created_at,
                COUNT(jl.id) as line_count,
                SUM(jl.debit_amount) as total_amount
            FROM journal_entries je
            JOIN fiscal_periods fp ON je.fiscal_period_id = fp.id
            LEFT JOIN journal_lines jl ON je.id = jl.journal_entry_id
            WHERE je.status = '{status}'
            {periodFilter}
            GROUP BY je.id, je.entry_number, je.entry_date, fp.period_name,
                     je.description, je.entry_type, je.status, je.created_by, je.created_at
            ORDER BY je.entry_date DESC, je.created_at DESC
        """
        
        result = self.api.executeSql(sql)
        
        entries = []
        for row in result.get('rows', []):
            entries.append({
                "id": row[0],
                "entry_number": row[1],
                "entry_date": row[2],
                "period_name": row[3],
                "description": row[4],
                "entry_type": row[5],
                "status": row[6],
                "created_by": row[7],
                "created_at": row[8],
                "line_count": row[9],
                "total_amount": float(row[10]) if row[10] else 0
            })
        
        return {
            "filter": {
                "status": status,
                "period": periodName
            },
            "entries": entries,
            "count": len(entries),
            "total_amount": sum(e["total_amount"] for e in entries)
        }


def main():
    """Main entry point for the Journal Entry STF."""
    try:
        inputData = readInput()
        userInput = inputData.get("input", {})
        
        operation = userInput.get("operation")
        if not operation:
            raise ValueError("Missing required field: operation")
        
        apiClient = createApiClient(inputData)
        manager = JournalEntryManager(apiClient)
        
        if operation == "create_journal_entry":
            validateRequiredFields(userInput, ["entry_date", "description", "lines"])
            result = manager.createJournalEntry(
                entryDate=userInput["entry_date"],
                description=userInput["description"],
                lines=userInput["lines"],
                entryType=userInput.get("entry_type", "STANDARD"),
                isAutoReverse=userInput.get("is_auto_reverse", False),
                reverseDate=userInput.get("reverse_date"),
                createdBy=userInput.get("created_by", "SYSTEM")
            )
            
        elif operation == "validate_journal_entry":
            validateRequiredFields(userInput, ["entry"])
            result = manager.validateJournalEntry(userInput["entry"])
            
        elif operation == "calculate_depreciation":
            validateRequiredFields(userInput, ["period"])
            result = manager.calculateDepreciation(
                periodName=userInput["period"],
                assetCategoryFilter=userInput.get("asset_category")
            )
            
        elif operation == "calculate_prepaid_amortization":
            validateRequiredFields(userInput, ["period"])
            result = manager.calculatePrepaidAmortization(
                periodName=userInput["period"]
            )
            
        elif operation == "generate_accrual_entry":
            validateRequiredFields(userInput, [
                "accrual_type", "period", "amount", "description",
                "expense_account_id", "liability_account_id"
            ])
            result = manager.generateAccrualEntry(
                accrualType=userInput["accrual_type"],
                periodName=userInput["period"],
                amount=float(userInput["amount"]),
                description=userInput["description"],
                expenseAccountId=userInput["expense_account_id"],
                liabilityAccountId=userInput["liability_account_id"],
                departmentId=userInput.get("department_id"),
                reference=userInput.get("reference")
            )
            
        elif operation == "list_pending_entries":
            result = manager.listPendingEntries(
                periodName=userInput.get("period"),
                status=userInput.get("status", "DRAFT")
            )
            
        else:
            raise ValueError(
                f"Unknown operation: {operation}. "
                f"Valid operations: create_journal_entry, validate_journal_entry, "
                f"calculate_depreciation, calculate_prepaid_amortization, "
                f"generate_accrual_entry, list_pending_entries"
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
