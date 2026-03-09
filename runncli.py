import os
import sys
import click
import logging
from dotenv import load_dotenv
from lib.logger import setup_logger, logger
from lib.commands.set_actuals_to_assigned import set_actuals_to_assigned
from lib.commands.list_projects import list_projects
from lib.commands.list_assignments import list_assignments
from lib.commands.list_actuals import list_actuals
from lib.commands.set_actuals import set_actuals
from lib.commands.list_people import list_people

@click.group()
@click.option('--log-level', 
              type=click.Choice(['INFO', 'DEBUG', 'TRACE', 'WARNING', 'ERROR'], case_sensitive=False),
              default='INFO',
              help='Set the logging verbosity.')
@click.option('--json', 'json_output', is_flag=True, help='Output results as JSON on stdout.')
@click.pass_context
def cli(ctx, log_level, json_output):
    """Runncli - A multi-command CLI tool for interacting with the Runn.io API."""
    
    ctx.ensure_object(dict)
    ctx.obj['json_output'] = json_output
    
    # Setup logging
    numeric_level = getattr(logging, log_level.upper(), None)
    if log_level.upper() == 'TRACE':
        from lib.logger import TRACE_LEVEL_NUM
        numeric_level = TRACE_LEVEL_NUM
    
    setup_logger(level=numeric_level)
    
    # Load .env
    load_dotenv()
    
    logger.info(f"Starting runncli with log-level {log_level}")

# Register commands
cli.add_command(set_actuals_to_assigned)
cli.add_command(list_projects)
cli.add_command(list_assignments)
cli.add_command(list_actuals)
cli.add_command(set_actuals)
cli.add_command(list_people)

if __name__ == '__main__':
    cli()
