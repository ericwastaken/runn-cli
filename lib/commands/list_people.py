import click
import json
from ..logger import logger
from ..client import RunnClient

@click.command()
@click.option('--email', type=str, help='Filter by email (case-insensitive substring)')
@click.option('--firstName', 'first_name', type=str, help='Filter by first name (case-insensitive substring)')
@click.option('--lastName', 'last_name', type=str, help='Filter by last name (case-insensitive substring)')
@click.pass_context
def list_people(ctx, email, first_name, last_name):
    """List all people."""
    
    json_output = ctx.obj.get('json_output', False)
    client = RunnClient()
    
    logger.info(f"Fetching people (email={email}, firstName={first_name}, lastName={last_name})...")
    
    people = client.get_people(email=email, first_name=first_name, last_name=last_name)
    
    if json_output:
        # Sort people by last name, then first name
        sorted_people = sorted(people, key=lambda x: (x.lastName.lower(), x.firstName.lower()))
        output = [
            {
                "id": p.personId,
                "firstName": p.firstName,
                "lastName": p.lastName,
                "email": p.email
            } for p in sorted_people
        ]
        summary = {"total": len(people)}
        click.echo(json.dumps({"commandOutput": output, "commandSummary": summary}))
        return

    if not people:
        click.echo("No people found.")
        return

    # Sort people by last name, then first name
    sorted_people = sorted(people, key=lambda x: (x.lastName.lower(), x.firstName.lower()))

    click.echo(f"{'ID':<10} {'Name':<30} {'Email'}")
    click.echo(f"{'-'*9:<10} {'-'*29:<30} {'-'*30}")
    
    for p in sorted_people:
        full_name = f"{p.firstName} {p.lastName}"
        email_str = p.email if p.email else ""
        click.echo(f"{str(p.personId):<10} {full_name[:29]:<30} {email_str}")

    click.echo(f"\nTotal: {len(people)} people")
