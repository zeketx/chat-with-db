# E2E Test: Basic Query Execution

Test basic query functionality in the Chat with Database application (Streamlit UI).

## User Story

As a user  
I want to query my data using natural language  
So that I can access information without writing SQL

## Test Steps

1. Navigate to the `Application URL` (http://localhost:8501)
2. Take a screenshot of the initial state
3. **Verify** the page title contains "Database Query App"
4. **Verify** core UI elements are present:
   - "Ask a question about the database:" text input

5. Enter the query: "Show me the first 5 tracks from the Track table"
6. Take a screenshot of the query input
7. Press Enter or wait for Streamlit to process
8. **Verify** the "SQL Query:" subheader appears
9. **Verify** the SQL translation is displayed (should contain "SELECT" and "Track")
10. Take a screenshot of the SQL translation
11. **Verify** the "Query Results:" subheader appears and the results table contains data
12. Take a screenshot of the results

## Success Criteria
- Query input accepts text
- Streamlit processes the input and triggers execution
- Results display correctly in a dataframe
- SQL translation is shown
- At least 4 screenshots are taken
