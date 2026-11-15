use nuxiva_peer_core::{Envelope, PeerError, PeerResult};
use std::io;
use std::net::SocketAddr;
use tokio::net::UdpSocket;

pub const MAX_DATAGRAM: usize = 1200;

pub fn encode(envelope: &Envelope) -> PeerResult<Vec<u8>> {
    let bytes = serde_json::to_vec(envelope).map_err(|_| PeerError::Payload)?;
    if bytes.len() > MAX_DATAGRAM {
        return Err(PeerError::Limit);
    }
    Ok(bytes)
}

pub fn decode(bytes: &[u8]) -> PeerResult<Envelope> {
    if bytes.len() > MAX_DATAGRAM {
        return Err(PeerError::Limit);
    }
    serde_json::from_slice(bytes).map_err(|_| PeerError::Payload)
}

#[derive(Debug)]
pub struct Beacon {
    socket: UdpSocket,
}

impl Beacon {
    pub async fn bind(addr: SocketAddr) -> io::Result<Self> {
        let socket = UdpSocket::bind(addr).await?;
        socket.set_broadcast(true)?;
        Ok(Self { socket })
    }

    pub fn local_addr(&self) -> io::Result<SocketAddr> {
        self.socket.local_addr()
    }

    pub async fn send(&self, envelope: &Envelope, to: SocketAddr) -> io::Result<()> {
        let bytes =
            encode(envelope).map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e.code()))?;
        self.socket.send_to(&bytes, to).await.map(|_| ())
    }

    pub async fn recv(&self) -> io::Result<(Vec<u8>, SocketAddr)> {
        let mut buffer = vec![0u8; MAX_DATAGRAM + 1];
        let (n, from) = self.socket.recv_from(&mut buffer).await?;
        buffer.truncate(n);
        Ok((buffer, from))
    }
}
