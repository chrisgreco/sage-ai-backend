@echo off
echo === Sage AI Backend Deployment Script ===
echo.

REM Change to backend directory
cd /d "%~dp0"

REM Add all changes
echo Adding all changes...
git add .

REM Check if there are changes to commit
git diff-index --quiet HEAD --
if %errorlevel% neq 0 (
    REM Get commit message from user input
    set /p commit_msg="Enter commit message: "
    
    REM Commit changes
    echo Committing changes...
    git commit -m "!commit_msg!"
    
    REM Push to main branch
    echo Pushing to GitHub...
    git push origin main
    
    REM If push fails due to divergent branches, force push
    if %errorlevel% neq 0 (
        echo Push failed, using force push...
        git push --force-with-lease origin main
    )
    
    echo.
    echo ✅ Deployment complete!
) else (
    echo ❌ No changes to commit.
)

echo.
pause 