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
@click.option('--start-date', type=str, required=True, help='Start of date range (YYYY-MM-DD, inclusive)')
@click.option('--end-date', type=str, required=True, help='End of date range (YYYY-MM-DD, inclusive)')
@click.option('--project-ids', type=str, help='Comma-separated list of projectIds to include')
@click.option('--exclude-project-ids', type=str, help='Comma-separated list of projectIds to skip')
@click.option('--force-update', is_flag=True, help='Actually write changes to the API')
@click.option('--sum', 'sum_opt', is_flag=True, default=False, help='Output sum of planned and actual minutes')
@click.pass_context
def set_actuals_to_assigned(ctx, person_id, start_date, end_date, project_ids, exclude_project_ids, force_update, sum_opt, client=None):
    """Compare planned assignments against logged actuals and update if needed."""
    
    json_output = ctx.obj.get('json_output', False)
    
    # Check if client is provided in context (for testing)
    if client is None and ctx.obj and 'client' in ctx.obj:
        client = ctx.obj['client']
    
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

    # 1. Init Client (assuming token is available from context or env)
    if client is None:
        client = RunnClient()

    # 2. Fetch data
    logger.info(f"Starting set-actuals-to-assigned for person {person_id} from {start_date} to {end_date}")
    if project_ids:
        logger.info(f"Filtering to project-ids: {project_ids}")
    if exclude_project_ids:
        logger.info(f"Excluding project-ids: {exclude_project_ids}")
    
    logger.info("Fetching projects...")
    project_names = client.get_projects()
    
    logger.info("Fetching assignments...")
    assignments = client.get_assignments(person_id, start_date, end_date)
    if not assignments:
        if json_output:
            click.echo(json.dumps({
                "commandOutput": [],
                "commandSummary": {
                    "updatedCount": 0,
                    "alreadyCorrectCount": 0,
                    "errorCount": 0,
                    "mode": "LIVE" if force_update else "DRY RUN"
                }
            }))
        else:
            click.echo(f"No assignments found for person {person_id} in range {start_date} to {end_date}")
        return

    # 3. Resolve active projects
    found_project_ids = {a.projectId for a in assignments}
    
    active_projects = set()
    if project_ids:
        active_projects = {int(pid.strip()) for pid in project_ids.split(',')}
    else:
        active_projects = found_project_ids
        
    if exclude_project_ids:
        exclude_set = {int(pid.strip()) for pid in exclude_project_ids.split(',')}
        active_projects = active_projects - exclude_set

    logger.debug(f"Resolved active projects: {active_projects}")

    # 4. Fetch actuals
    # API filtering: Only if exactly ONE project_id is provided in the include list
    api_project_id = None
    if project_ids:
        pids = {pid.strip() for pid in project_ids.split(',')}
        if len(pids) == 1:
            api_project_id = int(list(pids)[0])

    logger.info("Fetching actuals...")
    if api_project_id:
        logger.debug(f"API filtering actuals by projectId: {api_project_id}")
    actuals = client.get_actuals(person_id, start_date, end_date, project_id=api_project_id)

    # Step 1 -- Build the assignment schedule
    assignment_schedule = {}
    for a in assignments:
        if a.projectId not in active_projects:
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
            date_str = dt.strftime("%Y-%m-%d")
            if a.isNonWorkingDay:
                logger.trace(f"Skipping {date_str} for project {a.projectId}: isNonWorkingDay=True")
                continue

            key = (date_str, a.projectId)
            assignment_schedule[key] = {
                "minutesPerDay": a.minutesPerDay,
                "roleId": a.roleId,
                "isBillable": a.isBillable
            }
    
    logger.trace(f"Assignment schedule: {assignment_schedule}")

    # Step 2 -- Build the actuals index
    actuals_index = {}
    for act in actuals:
        if act.projectId not in active_projects:
            continue
        key = (act.date, act.projectId)
        actual_total = act.billableMinutes + act.nonbillableMinutes
        
        if key in actuals_index:
            actuals_index[key]["totalMinutes"] += actual_total
            actuals_index[key]["billableMinutes"] += act.billableMinutes
            actuals_index[key]["nonbillableMinutes"] += act.nonbillableMinutes
        else:
            actuals_index[key] = {
                "totalMinutes": actual_total,
                "billableMinutes": act.billableMinutes,
                "nonbillableMinutes": act.nonbillableMinutes,
                "roleId": act.roleId
            }
    
    logger.trace(f"Actuals index: {actuals_index}")

    # Step 3 -- Compare and build update list
    updates = []
    
    results = []
    for (date_str, project_id), assigned_info in assignment_schedule.items():
        planned = assigned_info["minutesPerDay"]
        actual_info = actuals_index.get((date_str, project_id), {})
        actual_total = actual_info.get("totalMinutes", 0)
        
        project_name = project_names.get(project_id, f"ID:{project_id}")
            
        results.append({
            "date": date_str,
            "project_id": project_id,
            "project_name": project_name,
            "planned": planned,
            "actual_total": actual_total,
            "assigned_info": assigned_info
        })

    # Sort by project name then by date
    results.sort(key=lambda x: (x["project_name"], x["date"]))
    
    updated_count = 0
    correct_count = 0
    error_count = 0
    output_rows = []

    for res in results:
        date_str = res["date"]
        project_id = res["project_id"]
        project_name = res["project_name"]
        planned = res["planned"]
        actual_total = res["actual_total"]
        assigned_info = res["assigned_info"]

        # Include weekday in date string
        dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
        weekday_str = dt_obj.strftime("%A")
        
        action = "OK"
        needs_update = False
        
        if actual_total < planned:
            needs_update = True
            if force_update:
                action = f"UPDATED -> {planned} min"
            else:
                action = f"WOULD UPDATE -> {planned} min"
        
        output_rows.append({
            "date": date_str,
            "weekday": weekday_str,
            "projectId": project_id,
            "projectName": project_name,
            "planned": planned,
            "actual": actual_total,
            "action": action
        })
        
        if needs_update:
            new_actual = Actual(
                actualId=None,
                personId=person_id,
                projectId=project_id,
                roleId=assigned_info["roleId"],
                date=date_str,
                billableMinutes=planned if assigned_info["isBillable"] else 0,
                nonbillableMinutes=planned if not assigned_info["isBillable"] else 0
            )
            updates.append(new_actual)
            updated_count += 1
        else:
            correct_count += 1
            logger.info(f"OK projectId={project_id} date={date_str} minutes={actual_total}")

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
        "alreadyCorrectCount": correct_count,
        "errorCount": error_count,
        "mode": "LIVE" if force_update else "DRY RUN"
    }
    
    if sum_opt:
        total_planned = sum(res["planned"] for res in results)
        total_actual = sum(res["actual_total"] for res in results)
        summary["totalPlannedMinutes"] = total_planned
        summary["totalActualMinutes"] = total_actual
        summary["totalPlannedTime"] = format_minutes_short(total_planned)
        summary["totalActualTime"] = format_minutes_short(total_actual)

    if json_output:
        click.echo(json.dumps({
            "commandOutput": output_rows,
            "commandSummary": summary
        }))
        return

    # Table Output
    if force_update:
        click.echo("[LIVE] Writing changes to Runn API.\n")
    else:
        click.echo("[DRY RUN] No changes will be written. Pass --force-update to apply.\n")

    click.echo(f"{'Date':<22} {'ID':<10} {'Project':<25} {'Planned':<8} {'Actual':<8} {'Action'}")
    click.echo(f"{'-'*20:<22} {'-'*9:<10} {'-'*24:<25} {'-'*7:<8} {'-'*6:<8} {'-'*18}")

    for row in output_rows:
        display_date = f"{row['date']} {row['weekday']}"
        planned_str = f"{row['planned']} min"
        actual_str = f"{row['actual']} min"
        click.echo(f"{display_date:<22} {str(row['projectId']):<10} {row['projectName'][:24]:<25} {planned_str:<8} {actual_str:<8} {row['action']}")

    click.echo(f"\nSummary: {updated_count} {'updated' if force_update else 'would be updated'}, {correct_count} already correct" + (f", {error_count} errors" if force_update and error_count > 0 else ""))

    if sum_opt:
        click.echo(f"Total Planned: {summary['totalPlannedMinutes']} min ({summary['totalPlannedTime']})")
        click.echo(f"Total Actual: {summary['totalActualMinutes']} min ({summary['totalActualTime']})")
