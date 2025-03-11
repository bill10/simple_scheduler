# Simple Scheduler

## Overview

This is a python program that runs python scripts at a scheduled time.

## Tech Stack
- Python=3.11
- Modern python libraries and packages
- Use sqllite for local storage

## Requirements

### Frontend Requirements
* The frontend runs in a web browser.
* Use a dark theme.
* On homepage, it shows two lists of scheduled tasks: one for active tasks and one for inactive (paused) tasks.
  * For every task in the list, it shows the status of the last run (success, failure, no run yet), the scheduled time for next run, and total number of runs.
  * The user can click on a task to view its details. This opens the task detail page.
  * At the top of the list, there is a button to add a new task, which opens the add task page.
* On the add task page, 
  * The user can specify a name for the task.
  * The user can specify a description for the task.
  * The user can choose the script from the script folder to run.
  * The user can specify the schedule time following the cron format. For example, 0 0 8 * * * will run the script at 8:00 AM every day.
  * The user can specify the start time and end time. If the start time is not set, the task will be active immediately. If the end time is not set, the task will be active indefinitely.
  * The user can specify extra arguments to pass to the script.
  * It shows a button to create the task.
  * It shows a button to cancel the add task.
* On the edit task page,
  * User can edit the name, description, schedule time, and extra arguments.The script name is read-only.
  * It shows a button to save the task.
  * It shows a button to cancel the edit.
* On the task detail page, 
  * It shows the name, description, script name, schedule time, and extra arguments. 
  * It shows a button to pause/unpause the task, a button to edit the task, and a button to delete the task.
  * It shows a button to test-run the task now, and displays the task output in a modal. The test run data won't be stored in the DB.
  * It shows a calendar as blocks. Each block corresponds to a day. The color of the block indicates the status of all the runs of the task on that day.
    * If all runs started on that day are successful, the block is green.
    * If any run started on that day failed, the block is red.
    * If no run started on that day, the block is gray.
    * Clicking on the block will show the list of runs of the task on that day. For each run, it shows the status, the duration, and a button to view its log.
  * It shows a bar chart showing the duration of all runs of the task. 
    * x-axis is start time.
    * y-axis is duration in seconds. 
    * The bar is colored based on the status of the run: green for successful runs, red for failed runs.
  * Besides the bar chart, shows two numbers: the total number of runs and success rate. The success rate is the percentage of successful runs.

### Backend Requirements
* It should support all the functions of the frontend.
* The data for each task and each run of the task is stored in a sqllite database.
* The python script for each task is stored in a folder by the user.
* Each script should be run in a subprocess. Don't block the main process.
* The log of each run of the task is stored in a log file. All log files are stored in a logs folder. The location of each log file is stored in the database.
* Each script should take in position argument at 1st position. This argument is the string representation of the start time of the run of this script. 