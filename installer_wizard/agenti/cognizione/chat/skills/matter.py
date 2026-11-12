def matter_skill() -> tuple[str, dict]:
    try:
        from agenti.matter.coordinator import MatterCoordinator
        coord = MatterCoordinator.instance()
        st = coord.get_status()
        spec = st.get("spec", "1.6.1")
        nodes_count = st.get("controller_nodes_count", 0)
        endpoints_count = st.get("bridge_endpoints_count", 0)

        speech = f"Matter {spec}: {nodes_count} nodi controllati, {endpoints_count} endpoint esposti su Universal Bridge."
        ui = {
            "mode": "matter",
            "spec": spec,
            "nodes_count": nodes_count,
            "bridge_endpoints_count": endpoints_count,
            "nodes": coord.list_nodes(),
            "endpoints": coord.list_bridge_endpoints(),
        }
        return speech, ui
    except Exception:
        return "Modulo Matter non disponibile.", {"mode": "matter", "error": True}
