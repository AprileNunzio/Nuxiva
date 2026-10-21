#![forbid(unsafe_code)]

pub mod arbiter;
pub mod co_pilot;
pub mod deferred_queue;
pub mod intent_router;
pub mod manifest;
pub mod memory_cache;
pub mod morphology;
pub mod network_governor;
pub mod priority;
pub mod resource_governor;
pub mod task_governor;
pub mod z_stack;

pub use arbiter::{ArbitrationAction, ArbitrationResult, PriorityArbiter};
pub use co_pilot::{CoPilotAction, CoPilotActionKind, LiveCoPilotEngine};
pub use deferred_queue::{DeferredQueue, MAX_DEFERRED_EVENTS};
pub use intent_router::IntentRouter;
pub use manifest::{
    AssistantRequirement, ContextManifest, FocusLockLevel, GpuLoad, SafeZone, ViewportMode,
    VoiceInteraction,
};
pub use memory_cache::{FastSemanticMemory, MemoryEntry, MemoryHit};
pub use morphology::AssistantMorphology;
pub use network_governor::{
    ActiveRouteResult, ConnectionRoutingPolicy, GsmModem, InterfaceKind, IpAssignmentMode,
    NetworkGovernor, NetworkInterface, NodeNetworkProfile, VpnTunnel,
};
pub use priority::{NotificationEvent, NotificationPriority};
pub use resource_governor::{
    ComputeProvider, LocalEngineAction, RemoteServerEntry, ResourceGovernor, ResourcePlan,
    TargetAllocation,
};
pub use task_governor::{
    MeshDispatchResolution, MeshTaskGovernor, NodeComponent, NodeProfile, TechnicalEvaluation,
};
pub use z_stack::{ZLayer, ZLayerStack, ZLayerState};

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_chess_manifest() -> ContextManifest {
        ContextManifest::new(
            "app.nuxiva.chess",
            ViewportMode::ImmersiveStage,
            GpuLoad::Medium,
            AssistantRequirement::new(
                AssistantMorphology::FloatingOrb,
                AssistantMorphology::AmbientStream,
                VoiceInteraction::ContinuousCoPilot,
            )
            .with_safe_zones(vec![SafeZone::TopRight, SafeZone::BottomRight]),
            FocusLockLevel::Lock2Engaged,
        )
    }

    fn sample_cad3d_manifest() -> ContextManifest {
        ContextManifest::new(
            "app.nuxiva.cad3d",
            ViewportMode::ImmersiveStage,
            GpuLoad::High,
            AssistantRequirement::new(
                AssistantMorphology::AmbientStream,
                AssistantMorphology::AmbientStream,
                VoiceInteraction::ContinuousCoPilot,
            ),
            FocusLockLevel::Lock3Immersive,
        )
    }

    #[test]
    fn test_p0_preemption_on_chess() {
        let arbiter = PriorityArbiter::new();
        let chess = sample_chess_manifest();
        let event = NotificationEvent::new(
            "evt-1",
            NotificationPriority::P0Critical,
            "alarm_fire",
            "sensor_triggered",
            "sensor.smoke",
            1000,
        );

        let res = arbiter.arbitrate(&event, &chess);
        assert_eq!(res.action, ArbitrationAction::PreemptionTotal);
        assert!(res.suspend_primary_stage);
        assert_eq!(res.target_layer, ZLayer::Z4CriticalInterrupt);
        assert!(!res.should_defer);
    }

    #[test]
    fn test_p0_preemption_on_cad3d() {
        let arbiter = PriorityArbiter::new();
        let cad = sample_cad3d_manifest();
        let event = NotificationEvent::new(
            "evt-2",
            NotificationPriority::P0Critical,
            "alarm_security",
            "perimeter_breach",
            "security.guard",
            1001,
        );

        let res = arbiter.arbitrate(&event, &cad);
        assert_eq!(res.action, ArbitrationAction::PreemptionTotal);
        assert!(res.suspend_primary_stage);
        assert_eq!(res.target_layer, ZLayer::Z4CriticalInterrupt);
    }

    #[test]
    fn test_p1_intercom_routing() {
        let arbiter = PriorityArbiter::new();
        let chess = sample_chess_manifest();
        let cad = sample_cad3d_manifest();
        let event = NotificationEvent::new(
            "evt-3",
            NotificationPriority::P1High,
            "intercom_ring",
            "doorbell_event",
            "intercom",
            1002,
        );

        let res_chess = arbiter.arbitrate(&event, &chess);
        assert_eq!(res_chess.action, ArbitrationAction::SmartPip);
        assert_eq!(res_chess.assigned_safe_zone, Some(SafeZone::TopRight));
        assert_eq!(res_chess.target_layer, ZLayer::Z2ContextualHud);
        assert!(!res_chess.suspend_primary_stage);

        let res_cad = arbiter.arbitrate(&event, &cad);
        assert_eq!(res_cad.action, ArbitrationAction::VoiceInterject);
        assert_eq!(
            res_cad.target_morphology,
            AssistantMorphology::AmbientStream
        );
        assert_eq!(res_cad.target_layer, ZLayer::Z3Assistant);
    }

    #[test]
    fn test_p2_render_deferred_in_chess_and_cad3d() {
        let arbiter = PriorityArbiter::new();
        let chess = sample_chess_manifest();
        let cad = sample_cad3d_manifest();
        let idle = ContextManifest::idle_default();

        let event = NotificationEvent::new(
            "evt-4",
            NotificationPriority::P2Normal,
            "render_completed",
            "task_finished",
            "blender",
            1003,
        );

        let res_chess = arbiter.arbitrate(&event, &chess);
        assert_eq!(res_chess.action, ArbitrationAction::Deferral);
        assert!(res_chess.should_defer);

        let res_cad = arbiter.arbitrate(&event, &cad);
        assert_eq!(res_cad.action, ArbitrationAction::Deferral);
        assert!(res_cad.should_defer);

        let res_idle = arbiter.arbitrate(&event, &idle);
        assert_eq!(res_idle.action, ArbitrationAction::SmartPip);
        assert!(!res_idle.should_defer);
    }

    #[test]
    fn test_deferred_queue_lifecycle() {
        let mut queue = DeferredQueue::new();
        assert!(queue.is_empty());

        let event1 = NotificationEvent::new(
            "1",
            NotificationPriority::P2Normal,
            "backup_done",
            "status_ok",
            "sys",
            100,
        );
        let event2 = NotificationEvent::new(
            "2",
            NotificationPriority::P2Normal,
            "sync_done",
            "status_ok",
            "delivery",
            200,
        );

        queue.push(event1);
        queue.push(event2);
        assert_eq!(queue.len(), 2);

        let drained = queue.drain_all();
        assert_eq!(drained.len(), 2);
        assert!(queue.is_empty());
    }

    #[test]
    fn test_intent_router() {
        let router = IntentRouter::new();
        assert_eq!(
            router.resolve_intent("voice_trigger_chess"),
            Some("app.nuxiva.chess")
        );
        assert_eq!(
            router.resolve_intent("voice_trigger_cad3d"),
            Some("app.nuxiva.cad3d")
        );
        assert_eq!(
            router.resolve_intent("voice_trigger_idle"),
            Some("app.nuxiva.idle")
        );
        assert_eq!(
            router.resolve_intent("voice_trigger_whisper"),
            Some("app.nuxiva.whisper")
        );
        assert_eq!(router.resolve_intent("unrecognized_input"), None);
    }

    #[test]
    fn test_manifest_json_roundtrip() -> Result<(), serde_json::Error> {
        let chess = sample_chess_manifest();
        let json = serde_json::to_string(&chess)?;
        let decoded: ContextManifest = serde_json::from_str(&json)?;
        assert_eq!(chess, decoded);
        Ok(())
    }

    #[test]
    fn test_fast_semantic_memory_operations() {
        let mut memory = FastSemanticMemory::new(2);
        let e1 = MemoryEntry::new(
            "cmd.lights.on",
            vec![1.0, 0.0, 0.0],
            "response.lights_activated",
            "{}",
            100,
        );
        let e2 = MemoryEntry::new(
            "cmd.lights.off",
            vec![0.0, 1.0, 0.0],
            "response.lights_deactivated",
            "{}",
            200,
        );
        memory.insert(e1);
        memory.insert(e2);
        assert_eq!(memory.len(), 2);

        let hit_exact = memory.lookup("cmd.lights.on", &[], 0.8);
        assert!(hit_exact.is_some());
        if let Some(h) = hit_exact {
            assert_eq!(h.response_key, "response.lights_activated");
        }

        let hit_sim = memory.lookup("unknown", &[0.95, 0.05, 0.0], 0.8);
        assert!(hit_sim.is_some());
        if let Some(h) = hit_sim {
            assert_eq!(h.response_key, "response.lights_activated");
        }

        let e3 = MemoryEntry::new(
            "cmd.music.play",
            vec![0.0, 0.0, 1.0],
            "response.music_playing",
            "{}",
            300,
        );
        memory.insert(e3);
        assert_eq!(memory.len(), 2);
    }

    #[test]
    fn test_live_copilot_session_lifecycle() {
        let mut copilot = LiveCoPilotEngine::new();
        assert!(!copilot.is_live());

        let start_act =
            copilot.start_session("chess", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR");
        assert!(copilot.is_live());
        assert_eq!(start_act.action_kind, CoPilotActionKind::SpeakInsight);
        assert_eq!(start_act.insight_key, "copilot.game_started");

        let m1 = copilot.on_move_applied("e2e4", "board_state_1");
        assert_eq!(m1.action_kind, CoPilotActionKind::SpeakInsight);
        assert_eq!(m1.suggested_move, Some("e2e4".to_string()));

        let m2 = copilot.on_move_applied("e7e5", "board_state_2");
        assert_eq!(m2.action_kind, CoPilotActionKind::SpeakInsight);

        let m3 = copilot.on_move_applied("g1f3", "board_state_3");
        assert_eq!(m3.action_kind, CoPilotActionKind::SuggestMove);

        let end_act = copilot.end_session();
        assert!(!copilot.is_live());
        assert_eq!(end_act.action_kind, CoPilotActionKind::SpeakInsight);
        assert_eq!(end_act.insight_key, "copilot.game_ended");
    }

    #[test]
    fn test_resource_governor_hibernation_logic() {
        let mut governor = ResourceGovernor::new();
        governor.register_remote_server("srv_gpu", "192.168.1.50");
        governor.register_remote_server("srv_backup", "192.168.1.99:8080");

        governor.set_target_allocation(TargetAllocation {
            target_id: "agent_chess".to_string(),
            provider: ComputeProvider::OllamaLocal,
            model_name: "richardyoung/lfm2.5-24b-a2b".to_string(),
            node_url: None,
        });

        let plan_local = governor.evaluate_resource_plan();
        assert_eq!(
            plan_local.local_engine_action,
            LocalEngineAction::KeepActive
        );
        assert_eq!(plan_local.local_targets_count, 1);
        assert_eq!(plan_local.remote_targets_count, 0);

        governor.apply_global_default_to_all(
            ComputeProvider::OllamaRemote,
            "qwen2.5:7b",
            Some("192.168.1.50"),
        );

        let plan_remote = governor.evaluate_resource_plan();
        assert_eq!(
            plan_remote.local_engine_action,
            LocalEngineAction::Hibernate
        );
        assert_eq!(plan_remote.local_targets_count, 0);
        assert_eq!(plan_remote.remote_targets_count, 1);
        assert_eq!(
            plan_remote.reason_code,
            "resource.hibernate_zero_local_targets"
        );
        assert!(
            plan_remote
                .active_remote_urls
                .contains(&"http://192.168.1.50:11434".to_string())
        );
        assert!(
            plan_remote
                .dormant_remote_urls
                .contains(&"http://192.168.1.99:8080".to_string())
        );
    }

    #[test]
    fn test_normalize_ollama_url_variants() {
        assert_eq!(
            ResourceGovernor::normalize_ollama_url("192.168.1.50"),
            "http://192.168.1.50:11434"
        );
        assert_eq!(
            ResourceGovernor::normalize_ollama_url("http://192.168.1.50:8080/"),
            "http://192.168.1.50:8080"
        );
        assert_eq!(
            ResourceGovernor::normalize_ollama_url("   "),
            "http://127.0.0.1:11434"
        );
        assert_eq!(
            ResourceGovernor::normalize_ollama_url("https://remote.ai:11434"),
            "https://remote.ai:11434"
        );
    }

    #[test]
    fn test_mesh_task_governor_dispatch_and_delegation() {
        let mut governor = MeshTaskGovernor::new();

        let pc_a = NodeProfile {
            node_id: "pc_a".to_string(),
            node_name: "Workstation GPU".to_string(),
            total_cpu_cores: 16,
            total_ram_mb: 65536.0,
            has_gpu: true,
            gpu_name: Some("RTX 4090".to_string()),
            total_vram_mb: 24576.0,
            components: MeshTaskGovernor::get_default_components(true),
        };

        let pc_b = NodeProfile {
            node_id: "pc_b".to_string(),
            node_name: "Mini PC Office".to_string(),
            total_cpu_cores: 4,
            total_ram_mb: 8192.0,
            has_gpu: false,
            gpu_name: None,
            total_vram_mb: 0.0,
            components: MeshTaskGovernor::get_default_components(false),
        };

        governor.register_or_update_node(pc_a);
        governor.register_or_update_node(pc_b);

        let dispatch_a = governor.resolve_capability_dispatch("pc_a", "voice_studio");
        assert!(dispatch_a.is_local);
        assert_eq!(dispatch_a.assigned_node_id, "pc_a");
        assert_eq!(dispatch_a.reason_code, "mesh_dispatch_local");

        let dispatch_b = governor.resolve_capability_dispatch("pc_b", "voice_studio");
        assert!(!dispatch_b.is_local);
        assert_eq!(dispatch_b.assigned_node_id, "pc_a");
        assert_eq!(dispatch_b.reason_code, "mesh_dispatch_delegated_peer");

        governor.recompute_delegations();
        let pc_b_ref = governor.get_node("pc_b");
        assert!(pc_b_ref.is_some());
        if let Some(node) = pc_b_ref {
            let voice_comp = node.components.iter().find(|c| c.id == "voice_studio");
            assert_eq!(
                voice_comp.and_then(|c| c.delegated_to.as_ref()),
                Some(&"pc_a".to_string())
            );
        }

        let eval_a = governor.evaluate_node("pc_a");
        assert!(eval_a.is_some());
        if let Some(eval) = eval_a {
            assert_eq!(eval.overall_status, "optimal");
            assert!(
                eval.recommendations
                    .contains(&"rec_mesh_voice_host_active".to_string())
            );
        }

        let ok = governor.toggle_component("pc_a", "voice_studio", false);
        assert!(ok);

        let dispatch_disabled = governor.resolve_capability_dispatch("pc_b", "voice_studio");
        assert_eq!(
            dispatch_disabled.reason_code,
            "mesh_capability_disabled_cluster_wide"
        );
    }

    #[test]
    fn test_network_governor_failover_and_policies() {
        let mut net_gov = NetworkGovernor::new();
        let prof = NetworkGovernor::get_default_profile("server_alpha", Some("192.168.1.100"));
        net_gov.register_or_update_profile(prof);

        let initial_route = net_gov.determine_active_route("server_alpha");
        assert_eq!(initial_route.primary_interface, "eth0");
        assert_eq!(initial_route.status, "ethernet_primary_optimal");
        assert!(!initial_route.failover_triggered);
        assert!(initial_route.internet_reachable);

        let toggled = net_gov.toggle_interface("server_alpha", "eth0", false);
        assert!(toggled);

        let failover_wifi = net_gov.determine_active_route("server_alpha");
        assert_eq!(failover_wifi.primary_interface, "wlan0");
        assert_eq!(failover_wifi.status, "failover_to_wifi");
        assert!(failover_wifi.failover_triggered);
        assert!(failover_wifi.internet_reachable);

        let toggled_wifi = net_gov.toggle_interface("server_alpha", "wlan0", false);
        assert!(toggled_wifi);

        let failover_gsm = net_gov.determine_active_route("server_alpha");
        assert_eq!(failover_gsm.primary_interface, "wwan0");
        assert_eq!(failover_gsm.status, "failover_to_cellular_emergency");
        assert!(failover_gsm.failover_triggered);
        assert!(failover_gsm.internet_reachable);

        let policy_switch = net_gov.set_policy("server_alpha", ConnectionRoutingPolicy::WifiOnly);
        assert!(policy_switch);
        let wifi_only_route = net_gov.determine_active_route("server_alpha");
        assert_eq!(wifi_only_route.primary_interface, "none");
        assert_eq!(wifi_only_route.status, "wifi_disconnected");
        assert!(!wifi_only_route.internet_reachable);

        assert!(NetworkGovernor::is_valid_ipv4("192.168.1.100"));
        assert!(NetworkGovernor::is_valid_ipv4("10.0.0.1"));
        assert!(!NetworkGovernor::is_valid_ipv4("999.1.1.1"));
        assert!(!NetworkGovernor::is_valid_ipv4("not_an_ip"));

        let update_res = net_gov.update_interface_ip_config(
            "server_alpha",
            "eth0",
            IpAssignmentMode::Static,
            Some("192.168.1.200".to_string()),
            Some("255.255.255.0".to_string()),
            Some("192.168.1.1".to_string()),
            Some("1.1.1.1".to_string()),
            Some("8.8.8.8".to_string()),
        );
        assert!(update_res.is_ok());

        let prof_updated = net_gov.get_profile("server_alpha");
        assert!(prof_updated.is_some());
        if let Some(p) = prof_updated {
            let eth_iface = p.interfaces.iter().find(|i| i.name == "eth0");
            assert!(eth_iface.is_some());
            if let Some(eth) = eth_iface {
                assert_eq!(eth.ipv4.as_deref(), Some("192.168.1.200"));
                assert_eq!(eth.ip_mode, IpAssignmentMode::Static);
            }
        }
    }
}
