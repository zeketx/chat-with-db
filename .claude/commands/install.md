# Install & Prime

## Read
.env.example (never read .env)

## Read and Execute
.claude/commands/prime.md

## Run
- Remove the existing git remote: `git remote remove origin`
- Initialize a new git repository: `git init`
- Run `cp .env.example .env`
- Install Python dependencies: `pip install -r requirements.txt`
- Run `./scripts/copy_dot_env.sh` to copy the .env file if available. Note, the source codebase may not exist, proceed either way.

## Report
- Output the work you've just done in a concise bullet point list.
- If `.env` does not exist, instruct the user to create it by running `cp .env.example .env` and then fill in the required values:
  - `OPENAI_API_KEY` — required for natural language to SQL translation
  - `DB_URL` — path to the SQLite database file (e.g. `movies.db`)
- If `.env` exists, remind the user to verify the required values are set correctly.
- Mention: 'To setup your AFK Agent, be sure to update the remote repo url and push to a new repo so you have access to git issues and git prs:
  ```
  git remote add origin <your-new-repo-url>
  git push -u origin main
  ```'