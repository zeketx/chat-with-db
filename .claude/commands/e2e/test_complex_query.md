# E2E Test: Complex Query with Filtering

Test complex query capabilities with filtering conditions in the Streamlit UI.

## User Story

As a user  
I want to query data using natural language with complex filtering conditions  
So that I can retrieve specific subsets of data without needing to write SQL

## Test Steps

1. Navigate to the `Application URL` (http://localhost:8501)
2. Take a screenshot of the initial state
3. Enter: "Show me all tracks that are longer than 5 minutes and cost more than 1 dollar"
4. Take a screenshot of the query input
5. Press Enter to trigger execution
6. **Verify** "SQL Query:" and "Query Results:" subheaders appear
7. **Verify** the generated SQL contains a `WHERE` clause with conditions for `Milliseconds` and `UnitPrice` (assuming Chinook schema)
8. Take a screenshot of the SQL translation
9. **Verify** the results table contains data matching the criteria
10. Take a screenshot of the filtered results
11. **Verify** the "Select Plot Type:" radio buttons appear (since results are numeric)
12. Select "Bar Chart" and take a screenshot of the visualization

## Success Criteria
- Complex natural language is correctly interpreted
- SQL contains appropriate WHERE conditions
- Results are properly filtered
- Visualization options appear for numerical data
- No errors occur during execution
- 5 screenshots are taken
