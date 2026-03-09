import click
import json
from datetime import datetime
import os
from ..logger import logger
from ..client import RunnClient
from ..utils import format_minutes_short, format_minutes_long

@click.command()
@click.option('--person-id', type=int, required=True, help='Runn personId for the target person')
@click.option('--start-date', type=str, required=True, help='Start of date range (YYYY-MM-DD, inclusive)')
@click.option('--end-date', type=str, required=True, help='End of date range (YYYY-MM-DD, inclusive)')
@click.option('--project-ids', type=str, help='Comma-separated list of projectIds to include')
@click.option('--exclude-project-ids', type=str, help='Comma-separated list of projectIds to skip')
@click.option('--sum', 'sum_opt', is_flag=True, default=False, help='Output sum of actual minutes')
@click.pass_context
def list_actuals(ctx, person_id, start_date, end_date, project_ids, exclude_project_ids, sum_opt):
    """List actuals for a person in a date range."""
    
    json_output = ctx.obj.get('json_output', False)
    
    # Validate dates
    try:
        dt_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        dt_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        if dt_start > dt_end:
            click.echo(f"Error: start_date ({start_date}) cannot be after end_date ({end_date})", err=True)
            raise click.Abort()
    except ValueError as e:
        click.echo(f"Error parsing dates: {e}", err=True)
        raise click.Abort()

    client = RunnClient()
    
    # Resolve project lists
    include_set = set()
    if project_ids:
        include_set = {int(pid.strip()) for pid in project_ids.split(',')}
    
    exclude_set = set()
    if exclude_project_ids:
        exclude_set = {int(pid.strip()) for pid in exclude_project_ids.split(',')}

    # API filtering: Only if exactly ONE project_id is provided
    api_project_id = None
    if len(include_set) == 1:
        api_project_id = list(include_set)[0]

    logger.info(f"Fetching actuals for person {person_id} from {start_date} to {end_date}...")
    if api_project_id:
        logger.debug(f"API filtering by projectId: {api_project_id}")
    
    project_names = client.get_projects()
    actuals = client.get_actuals(person_id, start_date, end_date, project_id=api_project_id)
    
    if not actuals:
        if json_output:
            click.echo(json.dumps({
                "commandOutput": [],
                "commandSummary": {
                    "totalActualEntries": 0,
                    "totalMinutes": 0,
                    "totalTime": format_minutes_long(0)
                }
            }))
        else:
            click.echo(f"No actuals found for person {person_id} in range {start_date} to {end_date}")
        return

    # Prepare for display and filter client-side
    display_items = []
    for a in actuals:
        # Date filter just in case
        if not (start_date <= a.date <= end_date):
            continue
            
        # Client-side project filtering
        if include_set and a.projectId not in include_set:
            continue
        if exclude_set and a.projectId in exclude_set:
            continue
            
        date_str = a.date
        dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
        weekday_str = dt_obj.strftime("%A")
        project_name = project_names.get(a.projectId, f"ID:{a.projectId}")
        total_minutes = a.billableMinutes + a.nonbillableMinutes
        
        display_items.append({
            "date": date_str,
            "weekday": weekday_str,
            "projectId": a.projectId,
            "projectName": project_name,
            "total": total_minutes
        })

    # Sort by project name then by date
    display_items.sort(key=lambda x: (x["projectName"], x["date"]))

    total_count = len(display_items)
    total_actuals = sum(item['total'] for item in display_items)

    if json_output:
        click.echo(json.dumps({
            "commandOutput": display_items,
            "commandSummary": {
                "totalActualEntries": total_count,
                "totalMinutes": total_actuals,
                "totalTime": format_minutes_long(total_actuals)
            }
        }))
        return

    click.echo(f"{'Date':<22} {'ID':<10} {'Project':<30} {'Actual'}")
    click.echo(f"{'-'*20:<22} {'-'*9:<10} {'-'*29:<30} {'-'*7}")
    
    for item in display_items:
        display_date = f"{item['date']} {item['weekday']}"
        click.echo(f"{display_date:<22} {str(item['projectId']):<10} {item['projectName'][:29]:<30} {item['total']} min")

    click.echo(f"\nTotal: {total_count} actual entries total {format_minutes_long(total_actuals)}")
