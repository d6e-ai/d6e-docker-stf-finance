"""
Shared utility functions for D6E Finance STFs.

Overview:
    Common functions used across all finance STF modules including:
    - D6E API communication
    - Input/output handling
    - Error handling
    - Logging configuration

Limitations:
    - SQL execution is restricted by D6E policy system
    - No DDL operations allowed
"""

import sys
import json
import logging
import requests
from typing import Any, Dict, List, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def configureLogging(level: int = logging.INFO) -> logging.Logger:
    """
    Configure logging to stderr (stdout is reserved for output).
    
    Args:
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        stream=sys.stderr,
        level=level,
        format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s'
    )
    return logging.getLogger(__name__)


logger = configureLogging()


def createSession() -> requests.Session:
    """
    Create HTTP session with retry logic for resilient API calls.
    
    Returns:
        Configured requests session with retry handling
    """
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def readInput() -> Dict[str, Any]:
    """
    Read and parse JSON input from stdin.
    
    Returns:
        Parsed input dictionary containing:
        - workspace_id: UUID of the workspace
        - stf_id: UUID of this STF
        - caller: UUID of the calling entity (or null)
        - api_url: Internal API URL
        - api_token: Authentication token
        - input: User-defined parameters
        - sources: Previous step outputs
    
    Raises:
        ValueError: If input is not valid JSON
    """
    try:
        inputData = json.load(sys.stdin)
        logger.info(f"Received input for operation: {inputData.get('input', {}).get('operation', 'unknown')}")
        return inputData
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON input: {str(e)}")


def writeOutput(result: Dict[str, Any]) -> None:
    """
    Write successful result to stdout.
    
    Args:
        result: Result dictionary to output
    """
    output = {"output": result}
    print(json.dumps(output, default=str))


def writeError(error: Exception, errorType: Optional[str] = None) -> None:
    """
    Write error response to stdout and exit with code 1.
    
    Args:
        error: Exception that occurred
        errorType: Optional error type override
    """
    errorOutput = {
        "error": str(error),
        "type": errorType or type(error).__name__
    }
    print(json.dumps(errorOutput))
    sys.exit(1)


class D6eApiClient:
    """
    Client for D6E internal SQL API.
    
    Handles authentication and SQL execution against workspace databases.
    """
    
    def __init__(self, apiUrl: str, apiToken: str, workspaceId: str, stfId: str):
        """
        Initialize API client.
        
        Args:
            apiUrl: Base URL for D6E API
            apiToken: Authentication token
            workspaceId: Workspace UUID
            stfId: STF UUID for policy evaluation
        """
        self.apiUrl = apiUrl
        self.apiToken = apiToken
        self.workspaceId = workspaceId
        self.stfId = stfId
        self.session = createSession()
        
    def _getHeaders(self) -> Dict[str, str]:
        """Get standard headers for API requests."""
        return {
            "Authorization": f"Bearer {self.apiToken}",
            "X-Internal-Bypass": "true",
            "X-Workspace-ID": self.workspaceId,
            "X-STF-ID": self.stfId,
            "Content-Type": "application/json"
        }
    
    def executeSql(self, sql: str) -> Dict[str, Any]:
        """
        Execute SQL query via D6E API.
        
        Args:
            sql: SQL query to execute (SELECT only, no DDL)
        
        Returns:
            Query results as dictionary with:
            - columns: List of column names
            - rows: List of row data
        
        Raises:
            Exception: If SQL execution fails
        """
        url = f"{self.apiUrl}/api/v1/workspaces/{self.workspaceId}/sql"
        
        logger.debug(f"Executing SQL: {sql[:100]}...")
        
        try:
            response = self.session.post(
                url,
                json={"sql": sql},
                headers=self._getHeaders(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            raise Exception(f"SQL execution timeout. Query: {sql[:100]}...")
        except requests.RequestException as e:
            raise Exception(f"SQL execution failed: {str(e)}. Query: {sql[:100]}...")
    
    def executeMultipleSql(self, statements: List[str]) -> List[Dict[str, Any]]:
        """
        Execute multiple SQL statements sequentially.
        
        Args:
            statements: List of SQL queries
        
        Returns:
            List of results for each statement
        """
        results = []
        for sql in statements:
            results.append(self.executeSql(sql))
        return results


def createApiClient(inputData: Dict[str, Any]) -> D6eApiClient:
    """
    Create D6E API client from standard input data.
    
    Args:
        inputData: Parsed input from stdin
    
    Returns:
        Configured API client
    """
    return D6eApiClient(
        apiUrl=inputData["api_url"],
        apiToken=inputData["api_token"],
        workspaceId=inputData["workspace_id"],
        stfId=inputData["stf_id"]
    )


def validateRequiredFields(userInput: Dict[str, Any], requiredFields: List[str]) -> None:
    """
    Validate that all required fields are present in user input.
    
    Args:
        userInput: User input dictionary
        requiredFields: List of required field names
    
    Raises:
        ValueError: If any required field is missing
    """
    missingFields = [f for f in requiredFields if f not in userInput]
    if missingFields:
        raise ValueError(f"Missing required fields: {', '.join(missingFields)}")


def formatCurrency(amount: float, symbol: str = "$") -> str:
    """
    Format number as currency string.
    
    Args:
        amount: Numeric amount
        symbol: Currency symbol (default: $)
    
    Returns:
        Formatted currency string (e.g., "$1,234.56")
    """
    if amount < 0:
        return f"-{symbol}{abs(amount):,.2f}"
    return f"{symbol}{amount:,.2f}"


def formatPercentage(value: float, decimals: int = 1) -> str:
    """
    Format number as percentage string.
    
    Args:
        value: Numeric value (0.15 = 15%)
        decimals: Decimal places to show
    
    Returns:
        Formatted percentage string (e.g., "15.0%")
    """
    return f"{value * 100:.{decimals}f}%"


def calculateVariance(actual: float, budget: float) -> Dict[str, Any]:
    """
    Calculate variance between actual and budget amounts.
    
    Args:
        actual: Actual amount
        budget: Budget/comparison amount
    
    Returns:
        Dictionary with:
        - dollar_variance: Absolute difference
        - percentage_variance: Percentage difference
        - is_favorable: Whether variance is favorable (for expenses)
    """
    dollarVariance = actual - budget
    
    if budget != 0:
        percentageVariance = dollarVariance / abs(budget)
    else:
        percentageVariance = 0 if dollarVariance == 0 else float('inf')
    
    return {
        "dollar_variance": dollarVariance,
        "percentage_variance": percentageVariance,
        "is_favorable": dollarVariance < 0  # For expenses, negative variance is favorable
    }
