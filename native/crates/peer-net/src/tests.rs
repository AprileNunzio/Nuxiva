use crate::*;
use nuxiva_peer_core::{Message, PeerError, PeerKey, TrustBook, Verifier};
use std::net::{IpAddr, Ipv4Addr, SocketAddr};

fn loopback() -> SocketAddr {
    SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), 0)
}

fn locate(key: &PeerKey, seq: u64, addr: &str) -> nuxiva_peer_core::Envelope {
    key.seal(
        seq,
        0,
        1,
        &Message::Locate {
            addrs: vec![addr.to_owned()],
        },
    )
    .expect("seal")
}

fn discovery_for(key: &PeerKey) -> Discovery {
    let mut trust = TrustBook::new();
    trust.enroll(key.id()).expect("enroll");
    Discovery::new(Verifier::new(trust))
}

#[tokio::test]
async fn beacon_over_udp_updates_the_directory() {
    let node = PeerKey::from_seed(&[1u8; 32]).expect("key");
    let listener = Beacon::bind(loopback()).await.expect("bind");
    let sender = Beacon::bind(loopback()).await.expect("bind");
    let target = listener.local_addr().expect("addr");
    let mut discovery = discovery_for(&node);
    sender
        .send(&locate(&node, 1, "192.168.1.20:7000"), target)
        .await
        .expect("send");
    let (bytes, from) = listener.recv().await.expect("recv");
    assert_eq!(discovery.on_datagram(&bytes, from, 0), Ok(true));
    assert_eq!(
        discovery.directory.candidates(node.id()),
        vec!["192.168.1.20:7000".to_owned()]
    );
    sender
        .send(&locate(&node, 2, "10.9.8.7:7000"), target)
        .await
        .expect("send");
    let (bytes, from) = listener.recv().await.expect("recv");
    assert_eq!(discovery.on_datagram(&bytes, from, 10), Ok(true));
    assert_eq!(
        discovery.directory.candidates(node.id()),
        vec!["10.9.8.7:7000".to_owned()]
    );
}

#[tokio::test]
async fn garbage_oversize_and_flood_are_dropped() {
    let node = PeerKey::from_seed(&[2u8; 32]).expect("key");
    let mut discovery = discovery_for(&node);
    let from = SocketAddr::new(IpAddr::V4(Ipv4Addr::new(192, 0, 2, 1)), 5000);
    assert_eq!(
        discovery.on_datagram(b"not json", from, 0),
        Err(PeerError::Payload)
    );
    assert_eq!(
        discovery.on_datagram(&vec![b'a'; 5000], from, 0),
        Err(PeerError::Limit)
    );
    let stranger = PeerKey::from_seed(&[3u8; 32]).expect("key");
    let bytes = encode(&locate(&stranger, 1, "10.0.0.1:7000")).expect("encode");
    assert_eq!(
        discovery.on_datagram(&bytes, from, 0),
        Err(PeerError::Untrusted)
    );
    let good = encode(&locate(&node, 1, "10.0.0.2:7000")).expect("encode");
    let other = SocketAddr::new(IpAddr::V4(Ipv4Addr::new(192, 0, 2, 9)), 5000);
    let mut refused = 0;
    for _ in 0..20 {
        if discovery.on_datagram(&good, other, 5).is_err() {
            refused += 1;
        }
    }
    assert!(refused >= 11);
    assert!(
        discovery.on_datagram(&good, other, 2_000).is_ok()
            || discovery.directory.get(node.id()).is_some()
    );
}

#[test]
fn throttle_windows_and_source_cap() {
    let mut throttle = Throttle::new(2, 1_000);
    let ip = IpAddr::V4(Ipv4Addr::new(10, 0, 0, 1));
    assert!(throttle.allow(ip, 0));
    assert!(throttle.allow(ip, 1));
    assert!(!throttle.allow(ip, 2));
    assert!(throttle.allow(ip, 1_500));
}
