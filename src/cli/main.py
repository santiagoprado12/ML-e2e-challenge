"""Module with CLI commands."""

import os
from enum import Enum
from typing import List, Optional

import typer
from typing_extensions import Annotated

import src.ml_core.train as train_model
import src.ml_core.validation as validation_model
from src.configs import Configs
from src.db.db_manager.postgre_sql_manager import PostgreSQLManager
from src.utils.run_make import run_makefile

app = typer.Typer()


def create_enum(enum_name: str, values: List[str]) -> Enum:
    """Create an enumeration of values for CLI options.

    Args:
        enum_name (str): Name of the enumeration.
        values (List[str]): List of string values for the enumeration.

    Returns:
        Enum: Enumeration of the provided values.
    """
    return Enum(enum_name, {value: value for value in values})


# Retrieve model names from configuration and create ModelType enum
model_type_list = [model["name"] for model in Configs().models]
ModelType = create_enum("ModelType", model_type_list)


@app.command()
def train(
    model: Annotated[
        Optional[List[ModelType]],
        typer.Option(..., "-m", "--model", help="Model to train"),
    ],
    threshold: float = typer.Option(
        None,
        "--acc-threshold",
        "-th",
        help="Accuracy threshold for the model to be registered (between 0 and 1))",
    ),
):
    """Train the specified machine learning model(s).

    Args:
        model (Optional[List[ModelType]]): List of models to train.
        threshold (float): Accuracy threshold for model registration.
    """
    # If no threshold is provided, train without it
    if threshold is None:
        train_model.train([mod.value for mod in model])
    elif 0 <= threshold <= 1:
        train_model.train([mod.value for mod in model], threshold)
    else:
        typer.echo("Invalid input. Please enter a float number between 0 and 1.")
        raise typer.Abort()


@app.command()
def validation(
    threshold: float = typer.Option(
        None,
        "--acc-threshold",
        "-th",
        help="Accuracy threshold for retraining the model (between 0 and 1))",
    )
):
    """Validate the model and optionally retrain if it does not meet the threshold.

    Args:
        threshold (float): Accuracy threshold to decide whether to retrain the model.
    """
    score = validation_model.validate()

    # If threshold is provided, check if model needs retraining
    if threshold is not None:
        if 0 <= threshold <= 1:
            if score < threshold:
                typer.echo("The model is not good enough. Training a new model.")
                run_makefile("train")
        else:
            typer.echo("Invalid input. Please enter a float number between 0 and 1.")
            raise typer.Abort()


@app.command()
def test(
    coverage: bool = typer.Option(
        False,
        "--coverage",
        "-c",
        help="Run the tests with coverage",
        show_default=False,
    )
):
    """Run the test suite with or without code coverage.

    Args:
        coverage (bool): Whether to run tests with coverage.
    """
    if coverage:
        run_makefile("test-coverage")
    else:
        run_makefile("test")


@app.command("run-sql")
def run_sql_file(sql_file: str = typer.Option(..., help="The path of the SQL file")):
    """Run the SQL file against the PostgreSQL database.

    Args:
        sql_file (str): The path to the SQL file to be executed.
    """
    # Check if the provided SQL file exists
    if not os.path.exists(sql_file):
        typer.echo(f"Error: File '{sql_file}' does not exist.")
        raise typer.Exit()

    # Read the SQL file
    with open(sql_file, "r") as file:
        sql_query = file.read()

    # Initialize the PostgreSQL manager
    db_manager = PostgreSQLManager()

    try:
        db_manager.connect()
        # Execute the SQL query and fetch results into a DataFrame
        data = db_manager.fetch_to_dataframe(sql_query)
        typer.echo(f"Successfully executed SQL from '{sql_file}'.")
        typer.echo(data.to_string())
    except Exception as e:
        typer.echo(f"Error executing SQL: {e}")
    finally:
        db_manager.close()


if __name__ == "__main__":
    app()
