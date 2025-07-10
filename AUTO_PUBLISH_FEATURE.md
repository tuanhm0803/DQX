# Auto Publish Feature for Scheduler

## Overview
The scheduler module now includes an **Auto Publish** checkbox that allows scheduled scripts to automatically publish their results to the central `bad_detail` table after execution.

## What's New

### 1. Database Schema Changes
- Added `auto_publish` BOOLEAN column to `dq.dq_schedules` table
- Default value is `FALSE` to maintain backward compatibility
- Column includes proper documentation comment

### 2. Updated Data Models
- `ScheduleBase` schema now includes `auto_publish: bool = False`
- `ScheduleUpdate` schema includes `auto_publish: Optional[bool] = None`
- Maintains backward compatibility with existing schedules

### 3. Enhanced User Interface
- Added "Auto Publish Results" checkbox in schedule creation/edit forms
- Added helpful description text explaining the feature
- Updated schedule list table to show auto_publish status
- New "Auto Publish" column shows Yes/No for each schedule

### 4. Backend Implementation
- Updated all CRUD operations to handle `auto_publish` field
- Enhanced route handlers to process the checkbox value
- Proper form validation and boolean conversion

## Usage

### Creating a Schedule with Auto Publish
1. Navigate to the Scheduler page (`/schedules/`)
2. Fill in the schedule details (job name, script, timing, etc.)
3. Check the "Auto Publish Results" checkbox if you want automatic publishing
4. Save the schedule

### Editing Existing Schedules
1. Click "Edit" on any existing schedule
2. The current auto_publish setting will be shown
3. Check/uncheck the "Auto Publish Results" checkbox as needed
4. Save changes

### How Auto Publish Works
When `auto_publish` is enabled for a schedule:
- The script executes according to the cron schedule
- Results are first populated in the script's staging table (`stg.dq_script_{script_id}`)
- If auto_publish is TRUE, results are automatically published to `dq.bad_detail`
- This eliminates the need for manual publishing after each execution

## Migration for Existing Systems

If you have an existing `dq_schedules` table, run the migration script:

```sql
-- Run this in your database
\i migration_add_auto_publish.sql
```

Or manually execute:
```sql
ALTER TABLE dq.dq_schedules 
ADD COLUMN IF NOT EXISTS auto_publish BOOLEAN NOT NULL DEFAULT FALSE;
```

## Benefits

1. **Automated Workflow**: No manual intervention needed after script execution
2. **Selective Publishing**: Choose per-schedule whether to auto-publish
3. **Backward Compatible**: Existing schedules continue to work unchanged
4. **Clear UI**: Easy to see which schedules have auto-publish enabled
5. **Flexible**: Can be enabled/disabled at any time by editing the schedule

## API Changes

The API endpoints now support the `auto_publish` field:

- `POST /api/schedules/` - Include `auto_publish: true/false` in request body
- `PUT /api/schedules/{id}` - Include `auto_publish` to update the setting
- `GET /api/schedules/` - Response includes `auto_publish` field for each schedule
- `GET /api/schedules/{id}` - Response includes `auto_publish` field

## Files Modified

1. `DB_table_creation.txt` - Updated table schema
2. `app/schemas.py` - Added auto_publish to schedule schemas
3. `app/crud.py` - Updated all schedule CRUD operations
4. `app/routes/scheduler.py` - Enhanced route handlers
5. `app/templates/scheduler.html` - Added UI elements
6. `migration_add_auto_publish.sql` - Migration script for existing systems
