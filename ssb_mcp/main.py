from typing import Any

import feedparser
import httpx
import pandas as pd
from fastmcp import FastMCP
from pyjstat import pyjstat


mcp = FastMCP(name="ssb_mcp")


@mcp.tool()
def search(keywords: list[str]) -> list[dict[str, Any]]:
    """Searches the Statistics Norway (SSB) API using a list of keywords and returns the JSON response.

    This function constructs a query string by joining the given list of keywords with URL-encoded spaces ("%20"),
    then sends a GET request to the SSB API endpoint. The function parses and returns the JSON response.

    Args:
        keywords (list[str]): A list of keywords to be used in the search query.

    Returns:
        list[dict[str, Any]]: The JSON response from the SSB API, containing search results or data tables.

    Raises:
        httpx.HTTPStatusError: If the HTTP request returns an unsuccessful status code.

    Example:
        >>> search(["kpi", "sysselsetting"])
        {...JSON data...}
    """
    query = "%20".join(keywords)
    url = f"https://data.ssb.no/api/v0/no/table/?query={query}"

    with httpx.Client() as client:
        response = client.get(url)
        response.raise_for_status()
        text = response.json()

    return text


@mcp.tool()
def table_metadata(table_id: str) -> dict[str, Any]:
    """Retrieves metadata for a specific table from the Statistics Norway (SSB) API.

    This function sends a GET request to the SSB API to fetch detailed metadata
    for the table identified by the given table ID. The metadata typically includes
    information about the table’s dimensions, variables, labels, sources, and other
    structural properties.

    Args:
        table_id (str): The identifier of the table to retrieve metadata for.
                        This should correspond to a valid SSB table ID.

    Returns:
        dict[str, Any]: A JSON object containing metadata for the specified table.
              The structure includes fields such as table title, variables,
              dimensions, and any constraints or descriptions associated with it.

    Raises:
        httpx.HTTPStatusError: If the HTTP request fails or returns a non-success status code.

    Example:
        >>> metadata = table_metadata("09842")
        >>> print(metadata["title"])
        '09842: BNP og andre hovedstørrelser (kr per innbygger), etter statistikkvariabel og år'
    """
    url = f"https://data.ssb.no/api/v0/no/table/{table_id}"

    with httpx.Client() as client:
        response = client.get(url)
        response.raise_for_status()
        text = response.json()

    return text


@mcp.tool()
def read_table(table_id: str) -> pd.DataFrame:
    """Retrieves and parses data from a specific table in the Statistics Norway (SSB) API.

    This function sends a POST request to the SSB API to fetch statistical data for a given
    table ID in the `json-stat2` format. It then parses the response using the `pyjstat` library
    and returns the data as a pandas DataFrame.

    Args:
        table_id (str): The unique identifier of the SSB table to retrieve data from.

    Returns:
        pd.DataFrame: A pandas DataFrame (returned as JSON) containing the structured statistical data
              from the specified SSB table. Columns and rows represent different dimensions and variables
              defined in the table metadata.

    Raises:
        httpx.HTTPStatusError: If the HTTP request fails or returns a non-2xx status code.
        ValueError: If the response cannot be parsed correctly by `pyjstat`.

    Example:
        >>> df = read_table("13198")
        >>> df.head()
           tid        kjønn      alder       value
        0 2022        Menn       15-74         1234
        1 2022        Kvinner    15-74         1100
        ...
    """
    metadata = table_metadata(table_id)
    metadata_variables = metadata["variables"]
    variables = [
        {"code": variable["code"], "values": variable["values"]}
        for variable in metadata_variables
    ]

    sub_variables = _recursive_split(variables)

    queries = []
    for sub_query in sub_variables:
        queries.append(
            [
                {
                    "code": variable["code"],
                    "selection": {"filter": "item", "values": variable["values"]},
                }
                for variable in sub_query
            ]
        )

    url = f"https://data.ssb.no/api/v0/no/table/{table_id}"

    df = pd.DataFrame()

    for sub_query in queries:
        with httpx.Client() as client:
            response = client.post(url, json={"query": sub_query, "response": {"format": "json-stat2"}})
            response.raise_for_status()

        dataset = pyjstat.Dataset.read(response.text)
        sub_df = dataset.write("dataframe")
        df = sub_df if df.empty else pd.concat([df, sub_df], ignore_index=True)

    return df


@mcp.tool()
def latest_publications(date: str | None = None) -> list[Any]:
    """Fetches the latest publications from the Statistics Norway (SSB) StatBank RSS feed,
    optionally filtering by a specific publication date.

    This function retrieves and parses the RSS feed from SSB containing recent statistical
    publications. If a date is provided, it filters the results to include only the entries
    published on that date (based on the `ssbrss_date` field in the feed entries).

    Args:
        date (str | None): An optional ISO-formatted date string (e.g., "2025-05-02") to
            filter publications. If None, all available entries are returned.

    Returns:
        list[Any]: A list of parsed RSS entries. Each entry is a dictionary-like object
        containing metadata such as 'title', 'link', 'published', 'summary', and 'ssbrss_date'.

    Example:
        >>> latest = latest_publications()
        >>> print(latest[0].title)

        >>> filtered = latest_publications("2025-05-02")
        >>> for entry in filtered:
        ...     print(entry.title, entry.ssbrss_date)
    """
    url = "https://www.ssb.no/rss/statbank/"
    feed = feedparser.parse(url)

    if date:
        filtered_entries = [
            entry for entry in feed.entries
            if "ssbrss_date" in entry and entry.ssbrss_date == date
        ]
        return filtered_entries

    return feed.entries


def _count_combinations(variables: list[dict[str, Any]]) -> int:
    count = 1
    for variable in variables:
        count *= len(variable["values"])

    return count


def _recursive_split(variables: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    current_count = _count_combinations(variables)
    if current_count <= 300000:
        return [variables]

    largest_variable = max(variables, key=lambda x: x["values"])
    split_index = len(largest_variable["values"]) // 2

    p1 = largest_variable["values"][:split_index]
    p2 = largest_variable["values"][split_index:]

    sub_query1 = [
        {
            "code": variable["code"],
            "values": (p1 if variable == largest_variable else variable["values"])
        }
        for variable in variables
    ]

    sub_query2 = [
        {
            "code": variable["code"],
            "values": (p2 if variable == largest_variable else variable["values"])
        }
        for variable in variables
    ]

    return _recursive_split(sub_query1) + _recursive_split(sub_query2)


def app():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    app()
