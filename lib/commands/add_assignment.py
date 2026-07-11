import click
import json
from dataclasses import asdict
from datetime import datetime
from ..logger import logger
from ..client import RunnClient
from ..models import Assignment, AssignmentCreate
from ..utils import format_minutes_long


def _assignment_row(assignment: Assignment):
    return {
        "assignmentId": assignment.assignmentId,
        "personId": assignment.personId,
        "projectId": assignment.projectId,
        "roleId": assignment.roleId,
        "startDate": assignment.startDate,
        "endDate": assignment.endDate,
        "minutesPerDay": assignment.minutesPerDay,
        "isBillable": assignment.isBillable,
        "isNonWorkingDay": assignment.isNonWorkingDay,
        "note": assignment.note,
        "phaseId": assignment.phaseId,
        "workstreamId": assignment.workstreamId
    }


@click.command()
@click.option('--person-id', type=int, required=True, help='Runn personId for the target person')
@click.option('--project-id', type=int, required=True, help='Runn projectId for the target project')
@click.option('--role-id', type=int, required=True, help='Runn roleId for the assignment')
@click.option('--start-date', type=str, required=True, help='Start of date range (YYYY-MM-DD, inclusive)')
@click.option('--end-date', type=str, required=True, help='End of date range (YYYY-MM-DD, inclusive)')
@click.option('--minutes', type=int, required=True, help='Number of assigned minutes per day')
@click.option('--note', type=str, help='Assignment note')
@click.option('--billable/--non-billable', 'is_billable', default=None, help='Set whether the assignment is billable')
@click.option('--phase-id', type=int, help='Runn phaseId for the assignment')
@click.option('--workstream-id', type=int, help='Runn workstreamId for the assignment')
@click.option('--non-working-day', is_flag=True, help='Create a non-working-day assignment; requires a single-day range')
@click.option('--force-update', is_flag=True, help='Actually write changes to the API')
@click.pass_context
def add_assignment(ctx, person_id, project_id, role_id, start_date, end_date, minutes, note, is_billable, phase_id, workstream_id, non_working_day, force_update):
    """Create a project assignment for a person/resource."""
    json_output = ctx.obj.get('json_output', False)

    try:
        dt_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        dt_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        if dt_start > dt_end:
            click.echo(f"Error: start_date ({start_date}) cannot be after end_date ({end_date})", err=True)
            raise click.Abort()
    except ValueError as e:
        click.echo(f"Error parsing dates: {e}", err=True)
        raise click.Abort()

    if minutes < 0:
        click.echo("Error: minutes must be non-negative", err=True)
        raise click.Abort()

    if non_working_day and dt_start != dt_end:
        click.echo("Error: --non-working-day assignments must use the same start-date and end-date", err=True)
        raise click.Abort()

    assignment = AssignmentCreate(
        personId=person_id,
        projectId=project_id,
        roleId=role_id,
        startDate=start_date,
        endDate=end_date,
        minutesPerDay=minutes,
        note=note,
        isBillable=is_billable,
        phaseId=phase_id,
        workstreamId=workstream_id,
        isNonWorkingDay=non_working_day
    )

    payload = {key: value for key, value in asdict(assignment).items() if value is not None}
    output_rows = [{"action": "CREATE" if force_update else "WOULD CREATE", **payload}]
    summary = {
        "createdCount": 0,
        "plannedCount": 1,
        "mode": "LIVE" if force_update else "DRY RUN"
    }

    if force_update:
        client = RunnClient()
        logger.info(f"Creating assignment for person {person_id}, project {project_id} from {start_date} to {end_date}...")
        created_assignments = client.post_assignment(assignment)
        output_rows = [_assignment_row(a) for a in created_assignments]
        summary["createdCount"] = len(created_assignments)
        summary["plannedCount"] = len(created_assignments)

    summary["totalMinutesPerDay"] = minutes
    summary["totalTimePerDay"] = format_minutes_long(minutes)

    if json_output:
        click.echo(json.dumps({
            "commandOutput": output_rows,
            "commandSummary": summary
        }))
        return

    if force_update:
        click.echo(f"[LIVE] Created assignment for person {person_id} on project {project_id}.\n")
    else:
        click.echo(f"[DRY RUN] Would create assignment for person {person_id} on project {project_id}. Pass --force-update to apply.\n")

    click.echo(f"{'Action':<14} {'Assignment':<12} {'Person':<10} {'Project':<10} {'Role':<10} {'Start':<12} {'End':<12} {'Minutes'}")
    click.echo(f"{'-'*13:<14} {'-'*11:<12} {'-'*9:<10} {'-'*9:<10} {'-'*9:<10} {'-'*10:<12} {'-'*10:<12} {'-'*7}")
    for row in output_rows:
        click.echo(f"{row.get('action', 'CREATED'):<14} {str(row.get('assignmentId', '-')):<12} {str(row['personId']):<10} {str(row['projectId']):<10} {str(row['roleId']):<10} {row['startDate']:<12} {row['endDate']:<12} {row['minutesPerDay']} min")

    click.echo(f"\nSummary: {summary['createdCount'] if force_update else summary['plannedCount']} assignment segment(s) {'created' if force_update else 'would be created'}")
