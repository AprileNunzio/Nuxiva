use crate::announce::Hardware;

pub const AUTO_MIN_CORES: u32 = 4;
pub const AUTO_MIN_RAM_MB: u64 = 8192;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Profile {
    Satellite,
    SecondServer,
    Auto,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    Satellite,
    SecondServer,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Ceiling {
    pub second_server: bool,
}

impl Profile {
    #[must_use]
    pub fn parse(raw: &str) -> Self {
        match raw {
            "second_server" => Self::SecondServer,
            "auto" => Self::Auto,
            _ => Self::Satellite,
        }
    }

    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Satellite => "satellite",
            Self::SecondServer => "second_server",
            Self::Auto => "auto",
        }
    }
}

impl Mode {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Satellite => "satellite",
            Self::SecondServer => "second_server",
        }
    }
}

#[must_use]
pub fn resolve(profile: Profile, hardware: &Hardware, full_host: bool, ceiling: Ceiling) -> Mode {
    if !ceiling.second_server {
        return Mode::Satellite;
    }
    match profile {
        Profile::Satellite => Mode::Satellite,
        Profile::SecondServer => Mode::SecondServer,
        Profile::Auto => {
            let capable =
                hardware.cpu_cores >= AUTO_MIN_CORES && hardware.ram_mb >= AUTO_MIN_RAM_MB;
            if capable && full_host {
                Mode::SecondServer
            } else {
                Mode::Satellite
            }
        }
    }
}
