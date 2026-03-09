# runncli -- Python CLI for Runn.io

`runncli` is a multi-command CLI tool for interacting with the [Runn.io API](https://runn.io). It is built with `click` and uses `uv` 
for dependency management.

> **Note:** This project is not affiliated with Runn.io in any way.

## Overview

The primary purpose of `runncli` is to automate and streamline interactions with the Runn.io API. 
The current version includes:
- `set-actuals-to-assigned`: Synchronize planned assignments with logged actuals.
- `list-projects`: List all projects with optional archived project inclusion.
- `list-people`: List all people with optional email and name filters.
- `list-assignments`: View expanded daily assignments for a specific person and date range.
- `list-actuals`: View logged actuals for a specific person and date range.
- `set-actuals`: Manually set actual minutes for a person/project over a date range (requires an existing assignment).

---

## Command Reference: `set-actuals`

Manually set actual minutes for a person and project for each weekday in a date range. The command requires an 
existing assignment for each date to determine the `roleId` and billing status.

### Usage
```bash
runncli [GLOBAL_OPTIONS] set-actuals --person-id ID --project-id ID --start-date YYYY-MM-DD --end-date YYYY-MM-DD --minutes MINS [--force-update]
```

### Options
| Parameter | Type | Description |
|---|---|---|
| `--person-id` | `int` | **Required.** Runn personId for the target person. |
| `--project-id` | `int` | **Required.** Runn projectId for the target project. |
| `--start-date` | `string` | **Required.** Start of date range (YYYY-MM-DD, inclusive). |
| `--end-date` | `string` | **Required.** End of date range (YYYY-MM-DD, inclusive). |
| `--minutes` | `int` | **Required.** Number of minutes to set for each day. |
| `--force-update` | `flag` | Actually write changes to the API. Defaults to dry-run mode. |

---

## Prerequisites

- **Python**: Version 3.12 or higher.
- **uv**: A fast Python package installer and resolver. [Install uv](https://docs.astral.sh/uv/getting-started/installation/).
- **Runn API Token**: A valid bearer token for Runn API authentication.

---

## Quickstart for Command Line Users

If you just want to run the tool without modifying its source code, follow these steps:

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/ericwastaken/python-runn-cli.git
    cd python-runn-cli
    ```

2. **Configure the environment**:
   Copy the example `.env` file and add your token:
   ```bash
   cp .env.example .env
   # Edit .env and replace your_bearer_token_here with your actual token
   ```

3.  **Run the tool**:
    Use `uv run` to execute the CLI directly from the source. `uv` will automatically handle the environment and dependencies.
    ```bash
    # Show help
    uv run runncli --help

    # Run a dry-run of the set-actuals-to-assigned command
    uv run runncli set-actuals-to-assigned \
      --person-id 12345 \
      --start-date 2026-03-09 \
      --end-date 2026-03-13
    ```

    **Alternatively, using `uvx`**:
    You can also use `uvx` (or `uv tool run`) to run the tool without explicit cloning (as long as you have the `.env` 
    file in your current directory):
    ```bash
    # Run directly from the repository
    uvx --from git+https://github.com/ericwastaken/python-runn-cli.git runncli --help
    ```

---

## Quickstart for Developers

To set up a development environment where you can edit the source code and run the tool:

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/ericwastaken/python-runn-cli.git
    cd python-runn-cli
    ```

2.  **Create a virtual environment and install in editable mode**:
    ```bash
    uv venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    uv pip install -e .
    ```

3.  **Configure the environment**:
    Copy the example `.env` file and add your token:
    ```bash
    cp .env.example .env
    # Edit .env and replace your_bearer_token_here
    ```

4.  **Run the tool**:
    Since it was installed in editable mode, you can call `runncli` directly:
    ```bash
    runncli --help
    ```

---

## Configuration

`runncli` requires a `.env` file in the project root containing your Runn API token.

```
RUNN_API_TOKEN=your_bearer_token_here
```

The tool will exit with an error message if this token is missing or unset.

---

## Command Reference: [GLOBAL_OPTIONS]

Global options must appear **before** the subcommand name and apply to all commands.

### Available Global Options

| Parameter     | Type     | Description                                                |
|---------------|----------|------------------------------------------------------------|
| `--log-level` | `string` | Set the verbosity of logging output. Defaults to `INFO`.   |
| `--json`      | `flag`   | Output results in JSON format instead of formatted tables. |

### `--log-level`

Controls the amount of detail displayed during command execution. Must be one of:

- **INFO** (default): Normal operational progress and summaries.
- **DEBUG**: API request/response details and logic flow.
- **TRACE**: Full raw data dumps for deep troubleshooting.
- **WARNING**: Only warnings and errors.
- **ERROR**: Only error messages.

**Example:**

```bash
runncli --log-level DEBUG [sub-command] [sub-command arguments]
```

### `--json`

If this argument is passed, the output will be structured as compact JSON:
```json
{"commandOutput": [...], "commandSummary": {"key": "value", ...}}
```

**Example:**

```bash
runncli --json [sub-command] [sub-command arguments]
```

## Command Reference: `list-projects`

List all projects from the Runn.io account.

### Usage
```bash
runncli [GLOBAL_OPTIONS] list-projects [--include-archived] [--name FILTER]
```

### Options
| Parameter | Type | Description |
|---|---|---|
| `--include-archived` | `flag` | Include archived projects in the list. |
| `--name` | `string` | Case-insensitive substring match on project name. |

---

## Command Reference: `list-people`

List all people from the Runn.io account.

### Usage
```bash
runncli [GLOBAL_OPTIONS] list-people [--email EMAIL] [--firstName NAME] [--lastName NAME]
```

### Options
| Parameter | Type | Description |
|---|---|---|
| `--email` | `string` | Filter by email (case-insensitive substring). |
| `--firstName` | `string` | Filter by first name (case-insensitive substring). |
| `--lastName` | `string` | Filter by last name (case-insensitive substring). |

---

## Command Reference: `list-assignments`

View a person's expanded assignment schedule for a date range.

### Usage
```bash
runncli [GLOBAL_OPTIONS] list-assignments --person-id ID --start-date YYYY-MM-DD --end-date YYYY-MM-DD [--project-ids IDS] [--exclude-project-ids IDS]
```

### Options
| Parameter | Type | Description |
|---|---|---|
| `--person-id` | `int` | **Required.** Runn personId for the target person. |
| `--start-date` | `string` | **Required.** Start of date range (YYYY-MM-DD, inclusive). |
| `--end-date` | `string` | **Required.** End of date range (YYYY-MM-DD, inclusive). |
| `--project-ids` | `string` | Comma-separated list of projectIds to include. |
| `--exclude-project-ids` | `string` | Comma-separated list of projectIds to skip. |
| `--sum` | `flag` | Output sum of assigned minutes. (Included by default) |

---

## Command Reference: `list-actuals`

View logged actuals for a person in a date range.

### Usage
```bash
runncli [GLOBAL_OPTIONS] list-actuals --person-id ID --start-date YYYY-MM-DD --end-date YYYY-MM-DD [--project-ids IDS] [--exclude-project-ids IDS]
```

### Options
| Parameter | Type | Description |
|---|---|---|
| `--person-id` | `int` | **Required.** Runn personId for the target person. |
| `--start-date` | `string` | **Required.** Start of date range (YYYY-MM-DD, inclusive). |
| `--end-date` | `string` | **Required.** End of date range (YYYY-MM-DD, inclusive). |
| `--project-ids` | `string` | Comma-separated list of projectIds to include. |
| `--exclude-project-ids` | `string` | Comma-separated list of projectIds to skip. |
| `--sum` | `flag` | Output sum of actual minutes. (Included by default) |

---

## Command Reference: `set-actuals-to-assigned`

Given a person, a date range, and an optional list of projects, this command compares planned assignments against logged 
actuals. For any project/day where the actual total minutes are less than the planned assignment minutes, the command 
updates (or would update) the actual to match the plan.

### Usage

```bash
runncli [GLOBAL_OPTIONS] set-actuals-to-assigned [COMMAND_OPTIONS]
```

### Options

| Parameter               | Type | Description |
|-------------------------|---|---|
| `--person_id`           | `int` | **Required.** Runn personId for the target person. |
| `--start_date`          | `string` | **Required.** Start of date range (YYYY-MM-DD, inclusive). |
| `--end_date`            | `string` | **Required.** End of date range (YYYY-MM-DD, inclusive). |
| `--project-ids`         | `string` | Comma-separated list of projectIds to include. |
| `--exclude-project-ids` | `string` | Comma-separated list of projectIds to skip. |
| `--force-update`        | `flag` | Actually write changes to the API. Defaults to dry-run mode. |
| `--sum`                 | `flag` | Output sum of planned and actual minutes. |

### Examples

**Dry-run (Safety First)**
```bash
runncli set-actuals-to-assigned \
  --person-id 795204 \
  --start-date 2026-03-09 \
  --end-date 2026-03-13
```

**Live Run (Updating API)**
```bash
runncli set-actuals-to-assigned \
  --person-id 795204 \
  --start-date 2026-03-09 \
  --end-date 2026-03-13 \
  --force-update
```

**Filtering by Projects**

```bash
runncli set-actuals-to-assigned \
  --person-id 795204 \
  --start-date 2026-03-09 \
  --end-date 2026-03-13 \
  --project-ids "1849539, 1849543"
```

> [!IMPORTANT]  
> If your comma-separated lists contain spaces, you **must** wrap them in quotes to ensure they are parsed correctly by 
> your shell.

---

## Batch Updates

For `set-actuals-to-assigned` and `set-actuals`, the tool automatically uses the Runn.io Bulk Actuals API to perform 
updates in batches of 100 entries. This significantly reduces the number of network requests and improves performance 
for large date ranges.

---

