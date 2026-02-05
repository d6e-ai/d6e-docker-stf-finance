#!/usr/bin/env python3
"""
D6E Docker STF: Financial Statements Generator

Overview:
    Generates GAAP-formatted financial statements including:
    - Income Statement (P&L)
    - Balance Sheet
    - Cash Flow Statement (indirect method)
    Supports period-over-period comparison and flux analysis.

Main Operations:
    - generate_income_statement: Create income statement for a period
    - generate_balance_sheet: Create balance sheet as of period end
    - generate_cash_flow: Create cash flow statement
    - generate_trial_balance: Create trial balance report

Limitations:
    - Requires account_balances table populated with period-end balances
    - Cash flow statement uses indirect method only
    - Currency is single-currency (no multi-currency consolidation)
"""

import sys
import os

# Add shared module path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

from utils import (
    logger, readInput, writeOutput, writeError,
    createApiClient, validateRequiredFields,
    formatCurrency, formatPercentage, calculateVariance
)
from typing import Any, Dict, List, Optional
from decimal import Decimal


class FinancialStatementsGenerator:
    """
    Generates various financial statements from GL data.
    """
    
    def __init__(self, apiClient):
        """
        Initialize generator with API client.
        
        Args:
            apiClient: D6eApiClient instance for database access
        """
        self.api = apiClient
    
    def generateIncomeStatement(
        self,
        periodName: str,
        comparisonPeriodName: Optional[str] = None,
        departmentId: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate income statement for specified period.
        
        Args:
            periodName: Period to report (e.g., "2025-01")
            comparisonPeriodName: Optional comparison period
            departmentId: Optional department filter
        
        Returns:
            Income statement structure with line items and totals
        """
        logger.info(f"Generating income statement for period: {periodName}")
        
        # Build department filter
        deptFilter = f"AND a.department_id = '{departmentId}'" if departmentId else ""
        
        # Query current period data
        currentSql = f"""
            SELECT 
                coa.account_type,
                coa.account_category,
                coa.display_order,
                a.account_code,
                a.account_name,
                ab.ending_balance
            FROM account_balances ab
            JOIN accounts a ON ab.account_id = a.id
            JOIN chart_of_accounts coa ON a.chart_of_accounts_id = coa.id
            JOIN fiscal_periods fp ON ab.fiscal_period_id = fp.id
            WHERE fp.period_name = '{periodName}'
            AND coa.account_type IN ('REVENUE', 'EXPENSE')
            {deptFilter}
            ORDER BY coa.display_order, a.account_code
        """
        
        currentData = self.api.executeSql(currentSql)
        
        # Query comparison period if specified
        comparisonData = None
        if comparisonPeriodName:
            comparisonSql = currentSql.replace(
                f"fp.period_name = '{periodName}'",
                f"fp.period_name = '{comparisonPeriodName}'"
            )
            comparisonData = self.api.executeSql(comparisonSql)
        
        # Build income statement structure
        return self._buildIncomeStatement(
            currentData,
            comparisonData,
            periodName,
            comparisonPeriodName
        )
    
    def _buildIncomeStatement(
        self,
        currentData: Dict,
        comparisonData: Optional[Dict],
        periodName: str,
        comparisonPeriodName: Optional[str]
    ) -> Dict[str, Any]:
        """Build structured income statement from query results."""
        
        # Create lookup for comparison data
        comparisonLookup = {}
        if comparisonData:
            for row in comparisonData.get('rows', []):
                key = row[3]  # account_code
                comparisonLookup[key] = float(row[5]) if row[5] else 0
        
        # Initialize sections
        revenueItems = []
        costOfRevenueItems = []
        operatingExpenseItems = []
        otherIncomeExpenseItems = []
        
        totalRevenue = 0
        totalCostOfRevenue = 0
        totalOperatingExpenses = 0
        totalOtherIncomeExpense = 0
        
        # Comparison totals
        compTotalRevenue = 0
        compTotalCostOfRevenue = 0
        compTotalOperatingExpenses = 0
        compTotalOtherIncomeExpense = 0
        
        # Process rows
        for row in currentData.get('rows', []):
            accountType = row[0]
            accountCategory = row[1]
            accountCode = row[3]
            accountName = row[4]
            balance = float(row[5]) if row[5] else 0
            
            # Get comparison amount
            compBalance = comparisonLookup.get(accountCode, 0)
            
            # Calculate variance
            variance = calculateVariance(balance, compBalance) if comparisonData else None
            
            lineItem = {
                "account_code": accountCode,
                "account_name": accountName,
                "current_amount": balance,
                "comparison_amount": compBalance if comparisonData else None,
                "variance": variance
            }
            
            # Categorize by account type and category
            if accountType == 'REVENUE':
                # Revenue is stored as credit (negative), flip sign for display
                lineItem["current_amount"] = -balance
                lineItem["comparison_amount"] = -compBalance if comparisonData else None
                revenueItems.append(lineItem)
                totalRevenue += -balance
                compTotalRevenue += -compBalance
                
            elif accountType == 'EXPENSE':
                category = accountCategory.upper() if accountCategory else ''
                
                if 'COST' in category or 'COGS' in category:
                    costOfRevenueItems.append(lineItem)
                    totalCostOfRevenue += balance
                    compTotalCostOfRevenue += compBalance
                    
                elif 'OTHER' in category or 'INTEREST' in category:
                    otherIncomeExpenseItems.append(lineItem)
                    totalOtherIncomeExpense += balance
                    compTotalOtherIncomeExpense += compBalance
                    
                else:
                    operatingExpenseItems.append(lineItem)
                    totalOperatingExpenses += balance
                    compTotalOperatingExpenses += compBalance
        
        # Calculate derived totals
        grossProfit = totalRevenue - totalCostOfRevenue
        compGrossProfit = compTotalRevenue - compTotalCostOfRevenue
        
        operatingIncome = grossProfit - totalOperatingExpenses
        compOperatingIncome = compGrossProfit - compTotalOperatingExpenses
        
        incomeBeforeTax = operatingIncome - totalOtherIncomeExpense
        compIncomeBeforeTax = compOperatingIncome - compTotalOtherIncomeExpense
        
        # Build final statement
        statement = {
            "statement_type": "INCOME_STATEMENT",
            "period": periodName,
            "comparison_period": comparisonPeriodName,
            "sections": {
                "revenue": {
                    "label": "Revenue",
                    "items": revenueItems,
                    "total": totalRevenue,
                    "comparison_total": compTotalRevenue if comparisonData else None,
                    "variance": calculateVariance(totalRevenue, compTotalRevenue) if comparisonData else None
                },
                "cost_of_revenue": {
                    "label": "Cost of Revenue",
                    "items": costOfRevenueItems,
                    "total": totalCostOfRevenue,
                    "comparison_total": compTotalCostOfRevenue if comparisonData else None,
                    "variance": calculateVariance(totalCostOfRevenue, compTotalCostOfRevenue) if comparisonData else None
                },
                "gross_profit": {
                    "label": "Gross Profit",
                    "total": grossProfit,
                    "comparison_total": compGrossProfit if comparisonData else None,
                    "variance": calculateVariance(grossProfit, compGrossProfit) if comparisonData else None,
                    "margin": grossProfit / totalRevenue if totalRevenue != 0 else 0,
                    "comparison_margin": compGrossProfit / compTotalRevenue if compTotalRevenue != 0 else None
                },
                "operating_expenses": {
                    "label": "Operating Expenses",
                    "items": operatingExpenseItems,
                    "total": totalOperatingExpenses,
                    "comparison_total": compTotalOperatingExpenses if comparisonData else None,
                    "variance": calculateVariance(totalOperatingExpenses, compTotalOperatingExpenses) if comparisonData else None
                },
                "operating_income": {
                    "label": "Operating Income",
                    "total": operatingIncome,
                    "comparison_total": compOperatingIncome if comparisonData else None,
                    "variance": calculateVariance(operatingIncome, compOperatingIncome) if comparisonData else None,
                    "margin": operatingIncome / totalRevenue if totalRevenue != 0 else 0
                },
                "other_income_expense": {
                    "label": "Other Income (Expense)",
                    "items": otherIncomeExpenseItems,
                    "total": -totalOtherIncomeExpense,
                    "comparison_total": -compTotalOtherIncomeExpense if comparisonData else None
                },
                "income_before_tax": {
                    "label": "Income Before Income Taxes",
                    "total": incomeBeforeTax,
                    "comparison_total": compIncomeBeforeTax if comparisonData else None,
                    "variance": calculateVariance(incomeBeforeTax, compIncomeBeforeTax) if comparisonData else None
                }
            }
        }
        
        return statement
    
    def generateBalanceSheet(
        self,
        periodName: str,
        comparisonPeriodName: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate balance sheet as of specified period end.
        
        Args:
            periodName: Period to report (e.g., "2025-01")
            comparisonPeriodName: Optional comparison period
        
        Returns:
            Balance sheet structure with assets, liabilities, equity
        """
        logger.info(f"Generating balance sheet for period: {periodName}")
        
        # Query current period data
        currentSql = f"""
            SELECT 
                coa.account_type,
                coa.account_category,
                coa.display_order,
                coa.normal_balance,
                a.account_code,
                a.account_name,
                ab.ending_balance
            FROM account_balances ab
            JOIN accounts a ON ab.account_id = a.id
            JOIN chart_of_accounts coa ON a.chart_of_accounts_id = coa.id
            JOIN fiscal_periods fp ON ab.fiscal_period_id = fp.id
            WHERE fp.period_name = '{periodName}'
            AND coa.account_type IN ('ASSET', 'LIABILITY', 'EQUITY')
            ORDER BY coa.display_order, a.account_code
        """
        
        currentData = self.api.executeSql(currentSql)
        
        # Query comparison period if specified
        comparisonData = None
        if comparisonPeriodName:
            comparisonSql = currentSql.replace(
                f"fp.period_name = '{periodName}'",
                f"fp.period_name = '{comparisonPeriodName}'"
            )
            comparisonData = self.api.executeSql(comparisonSql)
        
        # Build balance sheet
        return self._buildBalanceSheet(currentData, comparisonData, periodName, comparisonPeriodName)
    
    def _buildBalanceSheet(
        self,
        currentData: Dict,
        comparisonData: Optional[Dict],
        periodName: str,
        comparisonPeriodName: Optional[str]
    ) -> Dict[str, Any]:
        """Build structured balance sheet from query results."""
        
        # Create comparison lookup
        comparisonLookup = {}
        if comparisonData:
            for row in comparisonData.get('rows', []):
                key = row[4]  # account_code
                comparisonLookup[key] = float(row[6]) if row[6] else 0
        
        # Initialize categories
        currentAssets = []
        nonCurrentAssets = []
        currentLiabilities = []
        nonCurrentLiabilities = []
        equityItems = []
        
        totalCurrentAssets = 0
        totalNonCurrentAssets = 0
        totalCurrentLiabilities = 0
        totalNonCurrentLiabilities = 0
        totalEquity = 0
        
        # Comparison totals
        compCurrentAssets = 0
        compNonCurrentAssets = 0
        compCurrentLiabilities = 0
        compNonCurrentLiabilities = 0
        compEquity = 0
        
        # Process rows
        for row in currentData.get('rows', []):
            accountType = row[0]
            accountCategory = row[1]
            normalBalance = row[3]
            accountCode = row[4]
            accountName = row[5]
            balance = float(row[6]) if row[6] else 0
            
            compBalance = comparisonLookup.get(accountCode, 0)
            
            # Adjust sign for display (assets=debit positive, liabilities/equity=credit positive)
            if normalBalance == 'CREDIT':
                balance = -balance
                compBalance = -compBalance
            
            lineItem = {
                "account_code": accountCode,
                "account_name": accountName,
                "current_amount": balance,
                "comparison_amount": compBalance if comparisonData else None,
                "variance": calculateVariance(balance, compBalance) if comparisonData else None
            }
            
            category = (accountCategory or '').upper()
            
            if accountType == 'ASSET':
                if 'CURRENT' in category or 'CASH' in category or 'RECEIVABLE' in category:
                    currentAssets.append(lineItem)
                    totalCurrentAssets += balance
                    compCurrentAssets += compBalance
                else:
                    nonCurrentAssets.append(lineItem)
                    totalNonCurrentAssets += balance
                    compNonCurrentAssets += compBalance
                    
            elif accountType == 'LIABILITY':
                if 'CURRENT' in category:
                    currentLiabilities.append(lineItem)
                    totalCurrentLiabilities += balance
                    compCurrentLiabilities += compBalance
                else:
                    nonCurrentLiabilities.append(lineItem)
                    totalNonCurrentLiabilities += balance
                    compNonCurrentLiabilities += compBalance
                    
            elif accountType == 'EQUITY':
                equityItems.append(lineItem)
                totalEquity += balance
                compEquity += compBalance
        
        totalAssets = totalCurrentAssets + totalNonCurrentAssets
        totalLiabilities = totalCurrentLiabilities + totalNonCurrentLiabilities
        totalLiabilitiesAndEquity = totalLiabilities + totalEquity
        
        compTotalAssets = compCurrentAssets + compNonCurrentAssets
        compTotalLiabilities = compCurrentLiabilities + compNonCurrentLiabilities
        compTotalLiabilitiesAndEquity = compTotalLiabilities + compEquity
        
        statement = {
            "statement_type": "BALANCE_SHEET",
            "period": periodName,
            "comparison_period": comparisonPeriodName,
            "sections": {
                "current_assets": {
                    "label": "Current Assets",
                    "items": currentAssets,
                    "total": totalCurrentAssets,
                    "comparison_total": compCurrentAssets if comparisonData else None
                },
                "non_current_assets": {
                    "label": "Non-Current Assets",
                    "items": nonCurrentAssets,
                    "total": totalNonCurrentAssets,
                    "comparison_total": compNonCurrentAssets if comparisonData else None
                },
                "total_assets": {
                    "label": "TOTAL ASSETS",
                    "total": totalAssets,
                    "comparison_total": compTotalAssets if comparisonData else None,
                    "variance": calculateVariance(totalAssets, compTotalAssets) if comparisonData else None
                },
                "current_liabilities": {
                    "label": "Current Liabilities",
                    "items": currentLiabilities,
                    "total": totalCurrentLiabilities,
                    "comparison_total": compCurrentLiabilities if comparisonData else None
                },
                "non_current_liabilities": {
                    "label": "Non-Current Liabilities",
                    "items": nonCurrentLiabilities,
                    "total": totalNonCurrentLiabilities,
                    "comparison_total": compNonCurrentLiabilities if comparisonData else None
                },
                "total_liabilities": {
                    "label": "Total Liabilities",
                    "total": totalLiabilities,
                    "comparison_total": compTotalLiabilities if comparisonData else None
                },
                "equity": {
                    "label": "Stockholders' Equity",
                    "items": equityItems,
                    "total": totalEquity,
                    "comparison_total": compEquity if comparisonData else None
                },
                "total_liabilities_and_equity": {
                    "label": "TOTAL LIABILITIES AND STOCKHOLDERS' EQUITY",
                    "total": totalLiabilitiesAndEquity,
                    "comparison_total": compTotalLiabilitiesAndEquity if comparisonData else None
                }
            },
            "validation": {
                "balanced": abs(totalAssets - totalLiabilitiesAndEquity) < 0.01,
                "difference": totalAssets - totalLiabilitiesAndEquity
            }
        }
        
        return statement
    
    def generateCashFlow(
        self,
        periodName: str,
        comparisonPeriodName: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate cash flow statement using indirect method.
        
        Args:
            periodName: Period to report
            comparisonPeriodName: Optional comparison period
        
        Returns:
            Cash flow statement with operating, investing, financing sections
        """
        logger.info(f"Generating cash flow statement for period: {periodName}")
        
        # Get net income
        netIncomeSql = f"""
            SELECT 
                SUM(CASE 
                    WHEN coa.account_type = 'REVENUE' THEN -ab.ending_balance
                    WHEN coa.account_type = 'EXPENSE' THEN -ab.ending_balance
                    ELSE 0
                END) as net_income
            FROM account_balances ab
            JOIN accounts a ON ab.account_id = a.id
            JOIN chart_of_accounts coa ON a.chart_of_accounts_id = coa.id
            JOIN fiscal_periods fp ON ab.fiscal_period_id = fp.id
            WHERE fp.period_name = '{periodName}'
            AND coa.account_type IN ('REVENUE', 'EXPENSE')
        """
        
        netIncomeResult = self.api.executeSql(netIncomeSql)
        netIncome = float(netIncomeResult.get('rows', [[0]])[0][0] or 0)
        
        # Get balance sheet changes for cash flow adjustments
        changesSql = f"""
            WITH current_period AS (
                SELECT a.account_code, a.account_name, coa.account_category,
                       coa.account_type, ab.ending_balance
                FROM account_balances ab
                JOIN accounts a ON ab.account_id = a.id
                JOIN chart_of_accounts coa ON a.chart_of_accounts_id = coa.id
                JOIN fiscal_periods fp ON ab.fiscal_period_id = fp.id
                WHERE fp.period_name = '{periodName}'
            ),
            prior_period AS (
                SELECT a.account_code, ab.ending_balance as prior_balance
                FROM account_balances ab
                JOIN accounts a ON ab.account_id = a.id
                JOIN fiscal_periods fp ON ab.fiscal_period_id = fp.id
                WHERE fp.period_name = (
                    SELECT period_name FROM fiscal_periods 
                    WHERE period_end < (SELECT period_start FROM fiscal_periods WHERE period_name = '{periodName}')
                    ORDER BY period_end DESC LIMIT 1
                )
            )
            SELECT 
                cp.account_type,
                cp.account_category,
                cp.account_code,
                cp.account_name,
                cp.ending_balance,
                COALESCE(pp.prior_balance, 0) as prior_balance,
                cp.ending_balance - COALESCE(pp.prior_balance, 0) as change
            FROM current_period cp
            LEFT JOIN prior_period pp ON cp.account_code = pp.account_code
            WHERE cp.account_type IN ('ASSET', 'LIABILITY')
            ORDER BY cp.account_type, cp.account_code
        """
        
        changesData = self.api.executeSql(changesSql)
        
        # Build cash flow statement
        operatingAdjustments = []
        workingCapitalChanges = []
        investingActivities = []
        financingActivities = []
        
        totalOperatingAdjustments = 0
        totalWorkingCapitalChanges = 0
        totalInvesting = 0
        totalFinancing = 0
        
        for row in changesData.get('rows', []):
            accountType = row[0]
            accountCategory = (row[1] or '').upper()
            accountCode = row[2]
            accountName = row[3]
            change = float(row[6]) if row[6] else 0
            
            if change == 0:
                continue
            
            item = {
                "account_code": accountCode,
                "account_name": accountName,
                "amount": change
            }
            
            # Classify based on account type and category
            if 'DEPRECIATION' in accountName.upper() or 'ACCUMULATED' in accountName.upper():
                # Add back depreciation (non-cash expense)
                item["amount"] = -change
                operatingAdjustments.append(item)
                totalOperatingAdjustments += -change
                
            elif accountType == 'ASSET' and 'CURRENT' in accountCategory:
                # Current asset increase = cash outflow (negative)
                item["amount"] = -change
                workingCapitalChanges.append(item)
                totalWorkingCapitalChanges += -change
                
            elif accountType == 'LIABILITY' and 'CURRENT' in accountCategory:
                # Current liability increase = cash inflow (positive)
                workingCapitalChanges.append(item)
                totalWorkingCapitalChanges += change
                
            elif accountType == 'ASSET' and ('FIXED' in accountCategory or 'PROPERTY' in accountCategory):
                # Fixed asset increase = investing outflow
                item["amount"] = -change
                investingActivities.append(item)
                totalInvesting += -change
                
            elif accountType == 'LIABILITY' and 'DEBT' in accountCategory:
                # Debt increase = financing inflow
                financingActivities.append(item)
                totalFinancing += change
        
        netCashFromOperating = netIncome + totalOperatingAdjustments + totalWorkingCapitalChanges
        netChangeInCash = netCashFromOperating + totalInvesting + totalFinancing
        
        statement = {
            "statement_type": "CASH_FLOW_STATEMENT",
            "method": "INDIRECT",
            "period": periodName,
            "sections": {
                "operating_activities": {
                    "label": "Cash Flows from Operating Activities",
                    "net_income": netIncome,
                    "adjustments": {
                        "label": "Adjustments to reconcile net income to net cash",
                        "items": operatingAdjustments,
                        "total": totalOperatingAdjustments
                    },
                    "working_capital_changes": {
                        "label": "Changes in operating assets and liabilities",
                        "items": workingCapitalChanges,
                        "total": totalWorkingCapitalChanges
                    },
                    "net_cash": netCashFromOperating
                },
                "investing_activities": {
                    "label": "Cash Flows from Investing Activities",
                    "items": investingActivities,
                    "net_cash": totalInvesting
                },
                "financing_activities": {
                    "label": "Cash Flows from Financing Activities",
                    "items": financingActivities,
                    "net_cash": totalFinancing
                },
                "summary": {
                    "net_change_in_cash": netChangeInCash,
                    "net_cash_from_operating": netCashFromOperating,
                    "net_cash_from_investing": totalInvesting,
                    "net_cash_from_financing": totalFinancing
                }
            }
        }
        
        return statement
    
    def generateTrialBalance(self, periodName: str) -> Dict[str, Any]:
        """
        Generate trial balance for specified period.
        
        Args:
            periodName: Period to report
        
        Returns:
            Trial balance with all accounts and debit/credit totals
        """
        logger.info(f"Generating trial balance for period: {periodName}")
        
        sql = f"""
            SELECT 
                a.account_code,
                a.account_name,
                coa.account_type,
                coa.account_category,
                coa.normal_balance,
                ab.ending_balance
            FROM account_balances ab
            JOIN accounts a ON ab.account_id = a.id
            JOIN chart_of_accounts coa ON a.chart_of_accounts_id = coa.id
            JOIN fiscal_periods fp ON ab.fiscal_period_id = fp.id
            WHERE fp.period_name = '{periodName}'
            ORDER BY a.account_code
        """
        
        data = self.api.executeSql(sql)
        
        items = []
        totalDebits = 0
        totalCredits = 0
        
        for row in data.get('rows', []):
            accountCode = row[0]
            accountName = row[1]
            accountType = row[2]
            normalBalance = row[4]
            balance = float(row[5]) if row[5] else 0
            
            debit = balance if normalBalance == 'DEBIT' else 0
            credit = -balance if normalBalance == 'CREDIT' else 0
            
            items.append({
                "account_code": accountCode,
                "account_name": accountName,
                "account_type": accountType,
                "debit": debit if debit > 0 else 0,
                "credit": credit if credit > 0 else 0
            })
            
            totalDebits += debit if debit > 0 else 0
            totalCredits += credit if credit > 0 else 0
        
        return {
            "statement_type": "TRIAL_BALANCE",
            "period": periodName,
            "items": items,
            "totals": {
                "total_debits": totalDebits,
                "total_credits": totalCredits,
                "difference": totalDebits - totalCredits,
                "balanced": abs(totalDebits - totalCredits) < 0.01
            }
        }


def main():
    """Main entry point for the Financial Statements STF."""
    try:
        inputData = readInput()
        userInput = inputData.get("input", {})
        
        # Validate operation
        operation = userInput.get("operation")
        if not operation:
            raise ValueError("Missing required field: operation")
        
        # Create API client and generator
        apiClient = createApiClient(inputData)
        generator = FinancialStatementsGenerator(apiClient)
        
        # Route to appropriate operation
        if operation == "generate_income_statement":
            validateRequiredFields(userInput, ["period"])
            result = generator.generateIncomeStatement(
                periodName=userInput["period"],
                comparisonPeriodName=userInput.get("comparison_period"),
                departmentId=userInput.get("department_id")
            )
            
        elif operation == "generate_balance_sheet":
            validateRequiredFields(userInput, ["period"])
            result = generator.generateBalanceSheet(
                periodName=userInput["period"],
                comparisonPeriodName=userInput.get("comparison_period")
            )
            
        elif operation == "generate_cash_flow":
            validateRequiredFields(userInput, ["period"])
            result = generator.generateCashFlow(
                periodName=userInput["period"],
                comparisonPeriodName=userInput.get("comparison_period")
            )
            
        elif operation == "generate_trial_balance":
            validateRequiredFields(userInput, ["period"])
            result = generator.generateTrialBalance(
                periodName=userInput["period"]
            )
            
        else:
            raise ValueError(
                f"Unknown operation: {operation}. "
                f"Valid operations: generate_income_statement, generate_balance_sheet, "
                f"generate_cash_flow, generate_trial_balance"
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
