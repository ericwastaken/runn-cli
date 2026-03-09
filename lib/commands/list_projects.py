import click
import json
from ..logger import logger
from ..client import RunnClient
import os

@click.command()
@click.option('--include-archived', is_flag=True, default=False, help='Include archived projects in the list')
@click.option('--name', 'project_name_filter', type=str, help='Case-insensitive substring match on project name')
@click.pass_context
def list_projects(ctx, include_archived, project_name_filter):
    """List all projects."""
    
    json_output = ctx.obj.get('json_output', False)
    client = RunnClient()
    
    logger.info(f"Fetching projects (includeArchived={include_archived}, name_filter={project_name_filter})...")
    
    # get_projects returns Dict[int, str] mapping id to name
    projects = client.get_projects(include_archived=include_archived, name_filter=project_name_filter)
    
    if json_output:
        # Sort projects by name
        sorted_projects = sorted(projects.items(), key=lambda x: x[1])
        output = [{"id": pid, "name": name} for pid, name in sorted_projects]
        summary = {"total": len(projects)}
        click.echo(json.dumps({"commandOutput": output, "commandSummary": summary}))
        return

    if not projects:
        click.echo("No projects found.")
        return

    click.echo(f"{'ID':<10} {'Project Name'}")
    click.echo(f"{'-'*9:<10} {'-'*30}")
    
    # Sort projects by name
    sorted_projects = sorted(projects.items(), key=lambda x: x[1])
    
    for pid, name in sorted_projects:
        click.echo(f"{str(pid):<10} {name}")

    click.echo(f"\nTotal: {len(projects)} projects")
