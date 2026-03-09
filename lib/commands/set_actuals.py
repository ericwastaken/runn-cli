import click
import json
from datetime import datetime
from dateutil.rrule import rrule, DAILY, MO, TU, WE, TH, FR
from ..logger import logger
from ..client import RunnClient
from ..models import Actual
from ..utils import format_minutes_short, format_minutes_long

@click.command()
@click.option('--person-id', type=int, required=True, help='Runn personId for the target person')
@click.option('--project-id', type=int, required=True, help='Runn projectId for the target project')
@click.option('--start-date', type=str, required=True, help='Start of date range (YYYY-MM-DD, inclusive)')
@click.option('--end-date', type=str, required=True, help='End of date range (YYYY-MM-DD, inclusive)')
@click.option('--minutes', type=int, required=True, help='Number of minutes to set for each day')
@click.option('--force-update', is_flag=True, help='Actually write changes to the API')
@click.option('--sum', 'sum_opt', is_flag=True, default=False, help='Output sum of actual minutes')
@click.pass_context
def set_actuals(ctx, person_id, project_id, start_date, end_date, minutes, force_update, sum_opt):
    """Set actual minutes for a person/project over a date range, only if an assignment exists."""
    
    json_output = ctx.obj.get('json_output', False)
    
    # 0. Validate dates
    try:
        dt_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        dt_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        if dt_start > dt_end:
            click.echo(f"Error: start_date ({start_date}) cannot be after end_date ({end_date})", err=True)
            raise click.Abort()
    except ValueError as e:
        click.echo(f"Error parsing dates: {e}", err=True)
        raise click.Abort()

    # 1. Init Client
    client = RunnClient()

    # 2. Fetch data
    logger.info(f"Starting set-actuals for person {person_id}, project {project_id} from {start_date} to {end_date}")
    
    logger.info("Fetching project info...")
    project_names = client.get_projects()
    project_name = project_names.get(project_id, f"ID:{project_id}")
    
    logger.info(f"Fetching assignments for person {person_id}, project {project_id}...")
    assignments = client.get_assignments(person_id, start_date, end_date, project_id=project_id)
    
    if not assignments:
        if json_output:
            click.echo(json.dumps({
                "commandOutput": [],
                "commandSummary": {
                    "updatedCount": 0,
                    "skippedCount": 0,
                    "errorCount": 0,
                    "mode": "LIVE" if force_update else "DRY RUN"
                }
            }))
        else:
            click.echo(f"No assignments found for person {person_id} on project {project_id} in range {start_date} to {end_date}")
        return

    # Build assignment schedule for the specific project
    assignment_schedule = {}
    for a in assignments:
        if a.projectId != project_id:
            continue
            
        a_start = datetime.strptime(a.startDate, "%Y-%m-%d").date()
        a_end = datetime.strptime(a.endDate, "%Y-%m-%d").date()
        
        # Intersection of assignment range and requested range
        start = max(dt_start, a_start)
        end = min(dt_end, a_end)
        
        if start > end:
            continue

        # Expand days
        for dt in rrule(DAILY, dtstart=start, until=end, byweekday=(MO, TU, WE, TH, FR)):
            if a.isNonWorkingDay:
                continue
            date_str = dt.strftime("%Y-%m-%d")
            assignment_schedule[date_str] = {
                "roleId": a.roleId,
                "isBillable": a.isBillable
            }

    # 3. Process each date in the requested range (weekdays)
    updated_count = 0
    skipped_count = 0
    error_count = 0
    updates = []
    output_rows = []

    # Iterate through all dates in requested range
    for dt in rrule(DAILY, dtstart=dt_start, until=dt_end, byweekday=(MO, TU, WE, TH, FR)):
        date_str = dt.strftime("%Y-%m-%d")
        weekday_str = dt.strftime("%A")
        
        row = {
            "date": date_str,
            "weekday": weekday_str,
            "projectId": project_id,
            "projectName": project_name,
            "minutes": minutes
        }
        
        if date_str not in assignment_schedule:
            row["action"] = "ERROR: No assignment"
            output_rows.append(row)
            skipped_count += 1
            continue
            
        assigned_info = assignment_schedule[date_str]
        
        action = "WOULD SET"
        if force_update:
            action = "SETTING"
        
        row["action"] = f"{action} -> {minutes} min"
        output_rows.append(row)
            
        new_actual = Actual(
            actualId=None,
            personId=person_id,
            projectId=project_id,
            roleId=assigned_info["roleId"],
            date=date_str,
            billableMinutes=minutes if assigned_info["isBillable"] else 0,
            nonbillableMinutes=minutes if not assigned_info["isBillable"] else 0
        )
        updates.append(new_actual)
        updated_count += 1

    if force_update and updates:
        try:
            client.post_actuals_bulk(updates)
            logger.info(f"Successfully posted {len(updates)} actuals via bulk API")
        except Exception as e:
            logger.error(f"Failed to perform bulk update: {e}")
            error_count = len(updates)
            updated_count = 0

    summary = {
        "updatedCount": updated_count,
        "skippedCount": skipped_count,
        "errorCount": error_count,
        "mode": "LIVE" if force_update else "DRY RUN"
    }

    if sum_opt:
        total_minutes = updated_count * minutes
        summary["totalMinutes"] = total_minutes
        summary["totalTime"] = format_minutes_long(total_minutes)

    if json_output:
        click.echo(json.dumps({
            "commandOutput": output_rows,
            "commandSummary": summary
        }))
        return

    # Table output
    if force_update:
        click.echo(f"[LIVE] Setting actuals to {minutes} min for project {project_name}.\n")
    else:
        click.echo(f"[DRY RUN] Would set actuals to {minutes} min for project {project_name}. Pass --force-update to apply.\n")

    click.echo(f"{'Date':<22} {'ID':<10} {'Project':<30} {'Action'}")
    click.echo(f"{'-'*20:<22} {'-'*9:<10} {'-'*29:<30} {'-'*18}")

    for row in output_rows:
        display_date = f"{row['date']} {row['weekday']}"
        click.echo(f"{display_date:<22} {str(row['projectId']):<10} {row['projectName'][:29]:<30} {row['action']}")

    click.echo(f"\nSummary: {updated_count} {'set' if force_update else 'would be set'}, {skipped_count} skipped (no assignment)" + (f", {error_count} errors" if force_update and error_count > 0 else ""))

    if sum_opt:
        click.echo(f"Total: {updated_count} actual entries total {format_minutes_long(updated_count * minutes)}")
