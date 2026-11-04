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
    text = " → ".join(node["city"] for node in nodes)
    if len(text) <= 250:
        return text
    # Keep long Q3 tours readable. The original complete route stays in
    # the expandable JSON rather than taking over the entire window.
    visible = " → ".join(node["city"] for node in nodes[:5])
    return f"{visible} → … ({len(nodes)} route points; full path in JSON)"


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
        # Each origin is distinct from the meeting city, so every
        # successful route contains at least one flight. Subtracting one
        # connection per traveler preserves the meeting-city ranking.
        connection_count = sum(
            max(result["distances"][key] - 1, 0)
            for key in ("from_a", "from_b", "from_c")
        )
        return RouteSummary(
            f"Meet in {result['meeting_city']['city']}",
            "Minimizes the combined number of directed flight legs. "
            "Connections count only intermediate stops.",
            f"{result['total_flights']} flight legs · {connection_count} connections",
            tuple(lines),
            tuple(legend),
        )

    raise ValueError(f"Unsupported question: {question}")
