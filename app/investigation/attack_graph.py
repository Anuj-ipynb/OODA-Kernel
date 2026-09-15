import logging
from typing import Any

import networkx as nx

from app.security.models import DetectionAlert, SecurityEvent

logger = logging.getLogger(__name__)


class AttackGraphBuilder:
    """
    NetworkX Attack Graph Builder correlates entities into directional attack topology:
    - Nodes: Host, User, Process, IP, Alert, Technique
    - Edges: LOGGED_IN_TO, EXECUTED_ON, CONNECTED_TO, TRIGGERED_ALERT
    """
    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def add_event(self, evt: SecurityEvent) -> None:
        evt_node = f"evt:{evt.event_id[:8]}"
        self.graph.add_node(evt_node, type="event", event_type=evt.event_type, severity=evt.severity)

        if evt.host_id:
            host_node = f"host:{evt.host_id}"
            self.graph.add_node(host_node, type="host", name=evt.host_id)
            self.graph.add_edge(evt_node, host_node, relation="OCCURRED_ON")

        if evt.user_id:
            user_node = f"user:{evt.user_id}"
            self.graph.add_node(user_node, type="user", name=evt.user_id)
            self.graph.add_edge(user_node, evt_node, relation="PERFORMED")
            if evt.host_id:
                host_node = f"host:{evt.host_id}"
                self.graph.add_edge(user_node, host_node, relation="LOGGED_IN_TO")

        if evt.process_name:
            proc_node = f"proc:{evt.process_name}"
            self.graph.add_node(proc_node, type="process", name=evt.process_name, pid=evt.process_id)
            self.graph.add_edge(evt_node, proc_node, relation="SPAWNED")
            if evt.host_id:
                host_node = f"host:{evt.host_id}"
                self.graph.add_edge(proc_node, host_node, relation="EXECUTED_ON")

        if evt.src_ip:
            src_node = f"ip:{evt.src_ip}"
            self.graph.add_node(src_node, type="ip", ip=evt.src_ip)
            self.graph.add_edge(src_node, evt_node, relation="SRC_ORIGIN")

        if evt.dst_ip:
            dst_node = f"ip:{evt.dst_ip}"
            self.graph.add_node(dst_node, type="ip", ip=evt.dst_ip)
            self.graph.add_edge(evt_node, dst_node, relation="CONNECTED_TO", port=evt.dst_port)

    def add_alert(self, alert: DetectionAlert) -> None:
        alert_node = f"alert:{alert.rule_id}"
        self.graph.add_node(alert_node, type="alert", title=alert.title, severity=alert.severity)

        for evt in alert.events:
            self.add_event(evt)
            evt_node = f"evt:{evt.event_id[:8]}"
            self.graph.add_edge(alert_node, evt_node, relation="TRIGGERED_BY")

        for ind in alert.indicators:
            ind_node = f"{ind.indicator_type.lower()}:{ind.value}"
            self.graph.add_node(ind_node, type=ind.indicator_type.lower(), value=ind.value)
            self.graph.add_edge(alert_node, ind_node, relation="ASSOCIATED_IOC")

    def get_attack_paths(self) -> list[list[str]]:
        """Finds paths connecting source IPs or Users to Target Hosts or Critical Alerts."""
        sources = [n for n, d in self.graph.nodes(data=True) if d.get("type") in ["ip", "user"]]
        targets = [n for n, d in self.graph.nodes(data=True) if d.get("type") in ["host", "alert"]]
        
        paths = []
        for s in sources:
            for t in targets:
                if s != t and nx.has_path(self.graph, s, t):
                    try:
                        paths.extend(nx.all_simple_paths(self.graph, s, t, cutoff=5))
                    except Exception as e:  # noqa: BLE001
                        logger.debug(f"Path search warning: {e}")
        return paths

    def to_dict(self) -> dict[str, Any]:
        """Serializes NetworkX graph to D3/JSON compatible format."""
        nodes = [{"id": n, **d} for n, d in self.graph.nodes(data=True)]
        edges = [{"source": u, "target": v, **d} for u, v, d in self.graph.edges(data=True)]
        return {"nodes": nodes, "edges": edges}

    def to_graphviz_dot(self) -> str:
        """Generates Graphviz DOT syntax string for visualization."""
        dot_lines = ["digraph AttackGraph {", "rankdir=LR;", "node [fontname=\"Helvetica\", shape=ellipse];"]
        
        type_colors = {
            "user": "#1F6FEB",
            "host": "#238636",
            "process": "#D29922",
            "ip": "#8957E5",
            "alert": "#DA3633",
            "event": "#484F58"
        }

        for n, d in self.graph.nodes(data=True):
            node_type = d.get("type", "event")
            color = type_colors.get(node_type, "#30363D")
            label = d.get("name") or d.get("title") or d.get("ip") or d.get("value") or n
            dot_lines.append(f'  "{n}" [label="{node_type.upper()}\\n{label}", style=filled, fillcolor="{color}", fontcolor=white];')

        for u, v, d in self.graph.edges(data=True):
            rel = d.get("relation", "")
            dot_lines.append(f'  "{u}" -> "{v}" [label="{rel}"];')

        dot_lines.append("}")
        return "\n".join(dot_lines)
