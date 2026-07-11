import click
import json
from ..logger import logger
from ..client import RunnClient


@click.command()
@click.option('--assignment-id', type=int, required=True, help='Runn assignment ID to delete')
@click.option('--force-update', is_flag=True, help='Actually delete the assignment through the API')
@click.pass_context
def delete_assignment(ctx, assignment_id, force_update):
    """Delete one assignment by assignment ID."""
    json_output = ctx.obj.get('json_output', False)

    if assignment_id <= 0:
        click.echo("Error: assignment-id must be a positive integer", err=True)
        raise click.Abort()

    output_rows = [{
        "assignmentId": assignment_id,
        "action": "DELETE" if force_update else "WOULD DELETE"
    }]
    summary = {
        "deletedCount": 0,
        "plannedCount": 1,
        "mode": "LIVE" if force_update else "DRY RUN"
    }

    if force_update:
        client = RunnClient()
        logger.info(f"Deleting assignment {assignment_id}...")
        response = client.delete_assignment(assignment_id)
        output_rows[0]["response"] = response
        summary["deletedCount"] = 1

    if json_output:
        click.echo(json.dumps({
            "commandOutput": output_rows,
            "commandSummary": summary
        }))
        return

    if force_update:
        click.echo(f"[LIVE] Deleted assignment {assignment_id}.")
    else:
        click.echo(f"[DRY RUN] Would delete assignment {assignment_id}. Pass --force-update to apply.")
