#!/usr/bin/env python3
"""
D6E Docker STF: Variance Analysis

Overview:
    Performs financial variance analysis including:
    - Budget vs Actual comparison
    - Period-over-Period analysis
    - Variance decomposition (price/volume/mix)
    - Waterfall chart data generation
    - Variance narrative generation

Main Operations:
    - analyze_budget_variance: Compare actual to budget
    - analyze_period_variance: Compare period-over-period
    - decompose_variance: Break down variance into drivers
    - generate_waterfall: Create waterfall chart data
    - generate_variance_narrative: Create explanatory text

Limitations:
    - Materiality thresholds are configurable but default to standard values
    - Narrative generation provides templates, not AI-generated text
    - Mix analysis requires segment-level data
"""

import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'shared'))

from utils import (
    logger, readInput, writeOutput, writeError,
    createApiClient, validateRequiredFields,
    formatCurrency, formatPercentage, calculateVariance
)


class VarianceAnalyzer:
    """
    Performs variance analysis on financial data.
    """
    
    # Default materiality thresholds
    DEFAULT_THRESHOLDS = {
        "large_accounts": {"dollar": 500000, "percentage": 0.05},    # >$10M accounts
        "medium_accounts": {"dollar": 100000, "percentage": 0.10},   # $1M-$10M accounts
        "small_accounts": {"dollar": 50000, "percentage": 0.15}      # <$1M accounts
    }
    
    def __init__(self, apiClient, thresholds: Optional[Dict] = None):
        """
        Initialize analyzer with API client.
        
        Args:
            apiClient: D6eApiClient instance
            thresholds: Optional custom materiality thresholds
        """
        self.api = apiClient
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS
    
    def analyzeBudgetVariance(
        self,
        periodName: str,
        budgetVersion: str = "ORIGINAL",
        accountType: Optional[str] = None,
        departmentId: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare actual results to budget.
        
        Args:
            periodName: Period to analyze
            budgetVersion: Budget version to compare
            accountType: Optional filter (REVENUE, EXPENSE)
            departmentId: Optional department filter
        
        Returns:
            Variance analysis with material variances flagged
        """
        logger.info(f"Analyzing budget variance for period: {periodName}")
        
        typeFilter = f"AND coa.account_type = '{accountType}'" if accountType else ""
        deptFilter = f"AND b.department_id = '{departmentId}'" if departmentId else ""
        
        sql = f"""
            SELECT 
                a.account_code,
                a.account_name,
                coa.account_type,
                coa.account_category,
                COALESCE(ab.ending_balance, 0) as actual,
                COALESCE(b.budget_amount, 0) as budget
            FROM accounts a
            JOIN chart_of_accounts coa ON a.chart_of_accounts_id = coa.id
            LEFT JOIN account_balances ab ON a.id = ab.account_id
            LEFT JOIN fiscal_periods fp ON ab.fiscal_period_id = fp.id AND fp.period_name = '{periodName}'
            LEFT JOIN budgets b ON a.id = b.account_id 
                AND b.fiscal_period_id = fp.id 
                AND b.budget_version = '{budgetVersion}'
            WHERE (ab.ending_balance IS NOT NULL OR b.budget_amount IS NOT NULL)
            AND coa.account_type IN ('REVENUE', 'EXPENSE')
            {typeFilter}
            {deptFilter}
            ORDER BY coa.account_type, a.account_code
        """
        
        result = self.api.executeSql(sql)
        
        variances = []
        totalActual = 0
        totalBudget = 0
        materialVariances = []
        
        for row in result.get('rows', []):
            accountCode = row[0]
            accountName = row[1]
            accountType = row[2]
            accountCategory = row[3]
            actual = float(row[4]) if row[4] else 0
            budget = float(row[5]) if row[5] else 0
            
            # Adjust signs for revenue (stored as credit)
            if accountType == 'REVENUE':
                actual = -actual
                budget = -budget
            
            dollarVariance = actual - budget
            pctVariance = dollarVariance / abs(budget) if budget != 0 else 0
            
            # Determine if favorable (revenue: actual > budget is favorable, expense: actual < budget)
            isFavorable = (accountType == 'REVENUE' and dollarVariance > 0) or \
                         (accountType == 'EXPENSE' and dollarVariance < 0)
            
            # Check materiality
            isMaterial = self._checkMateriality(budget, dollarVariance, pctVariance)
            
            varianceItem = {
                "account_code": accountCode,
                "account_name": accountName,
                "account_type": accountType,
                "account_category": accountCategory,
                "actual": actual,
                "budget": budget,
                "variance_dollar": dollarVariance,
                "variance_percent": pctVariance,
                "is_favorable": isFavorable,
                "is_material": isMaterial
            }
            
            variances.append(varianceItem)
            totalActual += actual
            totalBudget += budget
            
            if isMaterial:
                materialVariances.append(varianceItem)
        
        # Sort material variances by absolute dollar impact
        materialVariances.sort(key=lambda x: abs(x['variance_dollar']), reverse=True)
        
        return {
            "analysis_type": "BUDGET_VS_ACTUAL",
            "period": periodName,
            "budget_version": budgetVersion,
            "summary": {
                "total_actual": totalActual,
                "total_budget": totalBudget,
                "total_variance_dollar": totalActual - totalBudget,
                "total_variance_percent": (totalActual - totalBudget) / abs(totalBudget) if totalBudget != 0 else 0,
                "account_count": len(variances),
                "material_variance_count": len(materialVariances)
            },
            "variances": variances,
            "material_variances": materialVariances,
            "thresholds_used": self.thresholds
        }
    
    def analyzePeriodVariance(
        self,
        currentPeriod: str,
        comparisonPeriod: str,
        accountType: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare current period to prior period.
        
        Args:
            currentPeriod: Current period name
            comparisonPeriod: Comparison period name
            accountType: Optional filter
        
        Returns:
            Period-over-period variance analysis
        """
        logger.info(f"Analyzing period variance: {currentPeriod} vs {comparisonPeriod}")
        
        typeFilter = f"AND coa.account_type = '{accountType}'" if accountType else \
                     "AND coa.account_type IN ('REVENUE', 'EXPENSE')"
        
        sql = f"""
            WITH current_data AS (
                SELECT a.id, a.account_code, a.account_name, 
                       coa.account_type, coa.account_category,
                       ab.ending_balance as amount
                FROM accounts a
                JOIN chart_of_accounts coa ON a.chart_of_accounts_id = coa.id
                JOIN account_balances ab ON a.id = ab.account_id
                JOIN fiscal_periods fp ON ab.fiscal_period_id = fp.id
                WHERE fp.period_name = '{currentPeriod}'
                {typeFilter}
            ),
            prior_data AS (
                SELECT a.id, ab.ending_balance as amount
                FROM accounts a
                JOIN account_balances ab ON a.id = ab.account_id
                JOIN fiscal_periods fp ON ab.fiscal_period_id = fp.id
                WHERE fp.period_name = '{comparisonPeriod}'
            )
            SELECT 
                c.account_code,
                c.account_name,
                c.account_type,
                c.account_category,
                COALESCE(c.amount, 0) as current_amount,
                COALESCE(p.amount, 0) as prior_amount
            FROM current_data c
            LEFT JOIN prior_data p ON c.id = p.id
            ORDER BY c.account_type, c.account_code
        """
        
        result = self.api.executeSql(sql)
        
        variances = []
        
        for row in result.get('rows', []):
            accountCode = row[0]
            accountName = row[1]
            accountType = row[2]
            accountCategory = row[3]
            current = float(row[4]) if row[4] else 0
            prior = float(row[5]) if row[5] else 0
            
            # Adjust for revenue sign
            if accountType == 'REVENUE':
                current = -current
                prior = -prior
            
            dollarChange = current - prior
            pctChange = dollarChange / abs(prior) if prior != 0 else (float('inf') if current != 0 else 0)
            
            isMaterial = self._checkMateriality(prior, dollarChange, pctChange)
            
            variances.append({
                "account_code": accountCode,
                "account_name": accountName,
                "account_type": accountType,
                "account_category": accountCategory,
                "current_period": current,
                "prior_period": prior,
                "change_dollar": dollarChange,
                "change_percent": pctChange,
                "is_material": isMaterial,
                "direction": "increase" if dollarChange > 0 else "decrease" if dollarChange < 0 else "flat"
            })
        
        materialVariances = [v for v in variances if v['is_material']]
        materialVariances.sort(key=lambda x: abs(x['change_dollar']), reverse=True)
        
        return {
            "analysis_type": "PERIOD_OVER_PERIOD",
            "current_period": currentPeriod,
            "comparison_period": comparisonPeriod,
            "variances": variances,
            "material_variances": materialVariances,
            "summary": {
                "account_count": len(variances),
                "material_variance_count": len(materialVariances),
                "increases": len([v for v in variances if v['direction'] == 'increase']),
                "decreases": len([v for v in variances if v['direction'] == 'decrease']),
                "flat": len([v for v in variances if v['direction'] == 'flat'])
            }
        }
    
    def decomposeVariance(
        self,
        accountCode: str,
        periodName: str,
        comparisonPeriod: str,
        decompositionType: str = "PRICE_VOLUME"
    ) -> Dict[str, Any]:
        """
        Decompose variance into price, volume, and mix effects.
        
        Args:
            accountCode: Account to analyze
            periodName: Current period
            comparisonPeriod: Comparison period
            decompositionType: PRICE_VOLUME or RATE_MIX
        
        Returns:
            Decomposition of variance into contributing factors
        """
        logger.info(f"Decomposing variance for account: {accountCode}")
        
        # Get account data
        sql = f"""
            SELECT 
                a.account_name,
                coa.account_type,
                curr.ending_balance as current_balance,
                prior.ending_balance as prior_balance
            FROM accounts a
            JOIN chart_of_accounts coa ON a.chart_of_accounts_id = coa.id
            LEFT JOIN (
                SELECT ab.account_id, ab.ending_balance
                FROM account_balances ab
                JOIN fiscal_periods fp ON ab.fiscal_period_id = fp.id
                WHERE fp.period_name = '{periodName}'
            ) curr ON a.id = curr.account_id
            LEFT JOIN (
                SELECT ab.account_id, ab.ending_balance
                FROM account_balances ab
                JOIN fiscal_periods fp ON ab.fiscal_period_id = fp.id
                WHERE fp.period_name = '{comparisonPeriod}'
            ) prior ON a.id = prior.account_id
            WHERE a.account_code = '{accountCode}'
        """
        
        result = self.api.executeSql(sql)
        
        if not result.get('rows'):
            raise ValueError(f"Account not found: {accountCode}")
        
        row = result['rows'][0]
        accountName = row[0]
        accountType = row[1]
        currentBalance = float(row[2]) if row[2] else 0
        priorBalance = float(row[3]) if row[3] else 0
        
        # Adjust for account type
        if accountType == 'REVENUE':
            currentBalance = -currentBalance
            priorBalance = -priorBalance
        
        totalVariance = currentBalance - priorBalance
        
        # For demonstration, create a synthetic decomposition
        # In production, this would use actual volume/price data from transactions
        
        if decompositionType == "PRICE_VOLUME":
            # Synthetic decomposition (would need actual unit data)
            volumeEffect = totalVariance * 0.6  # Assume 60% volume
            priceEffect = totalVariance * 0.3   # Assume 30% price
            mixEffect = totalVariance * 0.1     # Assume 10% mix
            
            decomposition = {
                "type": "PRICE_VOLUME",
                "components": [
                    {
                        "name": "Volume Effect",
                        "amount": volumeEffect,
                        "percentage_of_variance": 0.6,
                        "description": "Change due to volume/quantity differences"
                    },
                    {
                        "name": "Price Effect",
                        "amount": priceEffect,
                        "percentage_of_variance": 0.3,
                        "description": "Change due to price/rate differences"
                    },
                    {
                        "name": "Mix Effect",
                        "amount": mixEffect,
                        "percentage_of_variance": 0.1,
                        "description": "Change due to product/segment mix shift"
                    }
                ]
            }
        else:
            # Rate/Mix decomposition
            rateEffect = totalVariance * 0.7
            mixEffect = totalVariance * 0.3
            
            decomposition = {
                "type": "RATE_MIX",
                "components": [
                    {
                        "name": "Rate Effect",
                        "amount": rateEffect,
                        "percentage_of_variance": 0.7,
                        "description": "Change due to rate/margin differences"
                    },
                    {
                        "name": "Mix Effect",
                        "amount": mixEffect,
                        "percentage_of_variance": 0.3,
                        "description": "Change due to composition shift"
                    }
                ]
            }
        
        return {
            "account_code": accountCode,
            "account_name": accountName,
            "current_period": periodName,
            "comparison_period": comparisonPeriod,
            "current_amount": currentBalance,
            "prior_amount": priorBalance,
            "total_variance": totalVariance,
            "decomposition": decomposition,
            "verification": {
                "components_sum": sum(c['amount'] for c in decomposition['components']),
                "reconciles": abs(sum(c['amount'] for c in decomposition['components']) - totalVariance) < 0.01
            },
            "note": "Decomposition is estimated. For accurate analysis, provide actual volume and price data."
        }
    
    def generateWaterfall(
        self,
        startValue: float,
        endValue: float,
        drivers: List[Dict],
        title: str = "Variance Waterfall"
    ) -> Dict[str, Any]:
        """
        Generate waterfall chart data.
        
        Args:
            startValue: Starting value (e.g., budget or prior period)
            endValue: Ending value (e.g., actual or current period)
            drivers: List of variance drivers with name and amount
            title: Chart title
        
        Returns:
            Waterfall chart data structure
        """
        logger.info(f"Generating waterfall: {title}")
        
        # Calculate any residual
        driversTotal = sum(d['amount'] for d in drivers)
        calculatedEnd = startValue + driversTotal
        residual = endValue - calculatedEnd
        
        # Build waterfall data
        waterfallBars = []
        runningTotal = startValue
        
        # Starting bar
        waterfallBars.append({
            "label": "Starting Value",
            "value": startValue,
            "running_total": startValue,
            "bar_type": "total",
            "formatted_value": formatCurrency(startValue)
        })
        
        # Driver bars
        for driver in drivers:
            runningTotal += driver['amount']
            waterfallBars.append({
                "label": driver['name'],
                "value": driver['amount'],
                "running_total": runningTotal,
                "bar_type": "increase" if driver['amount'] > 0 else "decrease",
                "formatted_value": formatCurrency(driver['amount']),
                "percentage_of_change": driver['amount'] / (endValue - startValue) if (endValue - startValue) != 0 else 0
            })
        
        # Add residual if significant
        if abs(residual) > 0.01:
            runningTotal += residual
            waterfallBars.append({
                "label": "Other / Rounding",
                "value": residual,
                "running_total": runningTotal,
                "bar_type": "increase" if residual > 0 else "decrease",
                "formatted_value": formatCurrency(residual)
            })
        
        # Ending bar
        waterfallBars.append({
            "label": "Ending Value",
            "value": endValue,
            "running_total": endValue,
            "bar_type": "total",
            "formatted_value": formatCurrency(endValue)
        })
        
        # Generate text-based waterfall
        textWaterfall = self._generateTextWaterfall(title, waterfallBars, startValue, endValue)
        
        return {
            "title": title,
            "start_value": startValue,
            "end_value": endValue,
            "total_change": endValue - startValue,
            "bars": waterfallBars,
            "text_representation": textWaterfall,
            "reconciliation": {
                "drivers_sum": driversTotal,
                "residual": residual,
                "reconciles": abs(residual) < 1
            }
        }
    
    def _generateTextWaterfall(
        self,
        title: str,
        bars: List[Dict],
        startValue: float,
        endValue: float
    ) -> str:
        """Generate text-based waterfall representation."""
        lines = [f"WATERFALL: {title}", ""]
        
        for bar in bars:
            if bar['bar_type'] == 'total':
                lines.append(f"{bar['label']:<40} {bar['formatted_value']:>15}")
            else:
                prefix = "[+]" if bar['value'] > 0 else "[-]"
                lines.append(f"  |--{prefix} {bar['label']:<34} {bar['formatted_value']:>15}")
        
        lines.append("")
        lines.append(f"Net Change: {formatCurrency(endValue - startValue)} ({formatPercentage((endValue - startValue) / abs(startValue) if startValue != 0 else 0)})")
        
        return "\n".join(lines)
    
    def generateVarianceNarrative(
        self,
        varianceItem: Dict,
        additionalContext: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate narrative explanation for a variance.
        
        Args:
            varianceItem: Variance data with amounts and flags
            additionalContext: Optional context for narrative
        
        Returns:
            Structured narrative with key points
        """
        logger.info(f"Generating narrative for: {varianceItem.get('account_name', 'unknown')}")
        
        accountName = varianceItem.get('account_name', 'Unknown Account')
        actual = varianceItem.get('actual', varianceItem.get('current_period', 0))
        budget = varianceItem.get('budget', varianceItem.get('prior_period', 0))
        dollarVariance = varianceItem.get('variance_dollar', varianceItem.get('change_dollar', 0))
        pctVariance = varianceItem.get('variance_percent', varianceItem.get('change_percent', 0))
        isFavorable = varianceItem.get('is_favorable', dollarVariance < 0)  # Default assumes expense
        
        favorability = "favorable" if isFavorable else "unfavorable"
        direction = "higher" if dollarVariance > 0 else "lower"
        
        # Generate narrative components
        headline = (
            f"{accountName}: {favorability.capitalize()} variance of {formatCurrency(abs(dollarVariance))} "
            f"({formatPercentage(abs(pctVariance))})"
        )
        
        summary = (
            f"Actual of {formatCurrency(actual)} was {formatCurrency(abs(dollarVariance))} {direction} "
            f"than comparison amount of {formatCurrency(budget)}."
        )
        
        # Template-based driver suggestions
        if abs(pctVariance) > 0.20:
            outlook = "This represents a significant deviation that warrants detailed investigation."
        elif abs(pctVariance) > 0.10:
            outlook = "This variance should be monitored in upcoming periods."
        else:
            outlook = "This variance is within normal operating range."
        
        # Action items
        actions = []
        if varianceItem.get('is_material', False):
            actions.append("Investigate root cause with business owner")
            actions.append("Document driver analysis for management review")
            if not isFavorable:
                actions.append("Assess impact on forecast and identify remediation steps")
        
        return {
            "account_code": varianceItem.get('account_code'),
            "account_name": accountName,
            "narrative": {
                "headline": headline,
                "summary": summary,
                "outlook": outlook,
                "additional_context": additionalContext
            },
            "key_figures": {
                "actual": actual,
                "comparison": budget,
                "variance_dollar": dollarVariance,
                "variance_percent": pctVariance,
                "favorability": favorability
            },
            "suggested_actions": actions,
            "template_format": (
                f"{accountName}: {favorability.capitalize()} variance of {formatCurrency(abs(dollarVariance))} "
                f"({formatPercentage(abs(pctVariance))}) vs [comparison basis] for [period]\n\n"
                f"Driver: [Primary driver description]\n"
                f"[2-3 sentences explaining the business reason]\n\n"
                f"Outlook: [One-time / Expected to continue / Improving / Deteriorating]\n"
                f"Action: [None required / Monitor / Investigate further / Update forecast]"
            )
        }
    
    def _checkMateriality(
        self,
        baseAmount: float,
        dollarVariance: float,
        pctVariance: float
    ) -> bool:
        """Check if variance exceeds materiality thresholds."""
        absBase = abs(baseAmount)
        absDollar = abs(dollarVariance)
        absPct = abs(pctVariance)
        
        if absBase > 10000000:
            thresholds = self.thresholds["large_accounts"]
        elif absBase > 1000000:
            thresholds = self.thresholds["medium_accounts"]
        else:
            thresholds = self.thresholds["small_accounts"]
        
        return absDollar >= thresholds["dollar"] or absPct >= thresholds["percentage"]


def main():
    """Main entry point for the Variance Analysis STF."""
    try:
        inputData = readInput()
        userInput = inputData.get("input", {})
        
        operation = userInput.get("operation")
        if not operation:
            raise ValueError("Missing required field: operation")
        
        apiClient = createApiClient(inputData)
        
        # Allow custom thresholds
        customThresholds = userInput.get("materiality_thresholds")
        analyzer = VarianceAnalyzer(apiClient, customThresholds)
        
        if operation == "analyze_budget_variance":
            validateRequiredFields(userInput, ["period"])
            result = analyzer.analyzeBudgetVariance(
                periodName=userInput["period"],
                budgetVersion=userInput.get("budget_version", "ORIGINAL"),
                accountType=userInput.get("account_type"),
                departmentId=userInput.get("department_id")
            )
            
        elif operation == "analyze_period_variance":
            validateRequiredFields(userInput, ["current_period", "comparison_period"])
            result = analyzer.analyzePeriodVariance(
                currentPeriod=userInput["current_period"],
                comparisonPeriod=userInput["comparison_period"],
                accountType=userInput.get("account_type")
            )
            
        elif operation == "decompose_variance":
            validateRequiredFields(userInput, ["account_code", "period", "comparison_period"])
            result = analyzer.decomposeVariance(
                accountCode=userInput["account_code"],
                periodName=userInput["period"],
                comparisonPeriod=userInput["comparison_period"],
                decompositionType=userInput.get("decomposition_type", "PRICE_VOLUME")
            )
            
        elif operation == "generate_waterfall":
            validateRequiredFields(userInput, ["start_value", "end_value", "drivers"])
            result = analyzer.generateWaterfall(
                startValue=float(userInput["start_value"]),
                endValue=float(userInput["end_value"]),
                drivers=userInput["drivers"],
                title=userInput.get("title", "Variance Waterfall")
            )
            
        elif operation == "generate_variance_narrative":
            validateRequiredFields(userInput, ["variance_item"])
            result = analyzer.generateVarianceNarrative(
                varianceItem=userInput["variance_item"],
                additionalContext=userInput.get("additional_context")
            )
            
        else:
            raise ValueError(
                f"Unknown operation: {operation}. "
                f"Valid operations: analyze_budget_variance, analyze_period_variance, "
                f"decompose_variance, generate_waterfall, generate_variance_narrative"
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
