"""Turn the C++ JSON response into readable information for the desktop GUI.

This module has no Qt or map dependency, so the course examples can be tested
without opening a graphical window.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteSummary:
    title: str
    detail: str
    metric: str
    lines: tuple[str, ...]
    legend: tuple[tuple[str, str], ...] = ()
    warning: str = ""


Q4_COLORS = {
    "from_a": "#60A5FA",
    "from_b": "#FB923C",
    "from_c": "#C084FC",
}


def route_names(nodes: list[dict]) -> str:
    return " → ".join(node["city"] for node in nodes)


def describe_result(result: dict) -> RouteSummary:
    question = result["query"]
    status = result.get("status")
    if status != "found":
        messages = {
            "unreachable": "No directed route exists for these inputs.",
            "connection_limit": "The shortest route exceeds the strict connection limit.",
            "no_tour": "No valid round trip visits all reachable cities before returning to the start.",
            "heuristic_failed": "The large-graph heuristic did not find a tour. A valid tour may still exist.",
        }
        title = {
            "q1": "No qualifying route",
            "q2": "Required route unavailable",
            "q3": "Round trip not found",
            "q4": "No common meeting city",
        }.get(question, "No result")
        detail = messages.get(status, "No qualifying result was found.")
        warning = "A heuristic failure does not prove that a route is impossible." if status == "heuristic_failed" else ""
        return RouteSummary(title, detail, status.replace("_", " ").upper() if status else "NOT FOUND", (), warning=warning)

    if question == "q1":
        flights = result["flights"]
        connections = result["connections"]
        nodes = result["route"]
        if flights == 0:
            return RouteSummary(
                "Already at destination",
                "The starting city and destination are the same.",
                "0 flights · 0 connections",
                (route_names(nodes),),
            )
        return RouteSummary(
            "Shortest qualifying route",
            f"Connections: {connections}, strictly fewer than {result['exclusive_connection_limit']}.",
            f"{flights} flight{'s' if flights != 1 else ''} · {connections} connection{'s' if connections != 1 else ''}",
            (route_names(nodes),),
        )

    if question == "q2":
        names = [n["city"] for n in result.get("waypoint_order", [])]
        order = " → ".join(names) if names else "required cities included"
        return RouteSummary(
            "Shortest route through required cities",
            f"Required stops visited: {order}.",
            f"{result['flights']} flights · {result['connections']} connections",
            (route_names(result["route"]),),
        )

    if question == "q3":
        exact = result.get("optimal") is True and result.get("method") == "exact"
        return RouteSummary(
            "Shortest round trip" if exact else "Approximate round trip",
            f"Visits {result['reachable_cities']} reachable cities; starts and returns to the same city only at the end.",
            f"{result['flights']} flights · {'EXACT' if exact else 'HEURISTIC'}",
            (route_names(result["route"]),),
            warning=("" if exact else "This route is not guaranteed to use the fewest possible flights."),
        )

    if question == "q4":
        lines = []
        legend = []
        for key, label in (("from_a", "Traveler A"), ("from_b", "Traveler B"), ("from_c", "Traveler C")):
            path = result["routes"][key]
            distance = result["distances"][key]
            lines.append(f"{label}: {route_names(path)} ({distance} flights)")
            legend.append((label, Q4_COLORS[key]))
        return RouteSummary(
            f"Meet in {result['meeting_city']['city']}",
            "The meeting city minimizes the sum of directed flight legs from all three origins.",
            f"{result['total_flights']} total flight legs",
            tuple(lines),
            tuple(legend),
        )

    raise ValueError(f"Unsupported question: {question}")
