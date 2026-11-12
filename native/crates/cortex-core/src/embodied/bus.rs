use serde::{Deserialize, Serialize};

use crate::platform::error::{CortexError, CortexResult};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Cia402State {
    NotReadyToSwitchOn,
    SwitchOnDisabled,
    ReadyToSwitchOn,
    SwitchedOn,
    OperationEnabled,
    QuickStopActive,
    FaultReactionActive,
    Fault,
}

impl Cia402State {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::NotReadyToSwitchOn => "not_ready_to_switch_on",
            Self::SwitchOnDisabled => "switch_on_disabled",
            Self::ReadyToSwitchOn => "ready_to_switch_on",
            Self::SwitchedOn => "switched_on",
            Self::OperationEnabled => "operation_enabled",
            Self::QuickStopActive => "quick_stop_active",
            Self::FaultReactionActive => "fault_reaction_active",
            Self::Fault => "fault",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CanOpenPdoFrame {
    pub node_id: u8,
    pub cob_id: u32,
    pub data: [u8; 8],
    pub len: u8,
    pub is_rx: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EtherCatLrwFrame {
    pub logical_address: u32,
    pub payload: Vec<u8>,
    pub working_counter: u16,
    pub expected_working_counter: u16,
}

#[derive(Debug)]
pub struct FieldbusController;

impl FieldbusController {
    #[must_use]
    #[allow(clippy::fn_params_excessive_bools)]
    pub const fn encode_controlword(
        switch_on: bool,
        enable_voltage: bool,
        quick_stop: bool,
        enable_operation: bool,
        fault_reset: bool,
    ) -> u16 {
        let mut cw = 0_u16;
        if switch_on {
            cw |= 1 << 0;
        }
        if enable_voltage {
            cw |= 1 << 1;
        }
        if quick_stop {
            cw |= 1 << 2;
        }
        if enable_operation {
            cw |= 1 << 3;
        }
        if fault_reset {
            cw |= 1 << 7;
        }
        cw
    }

    #[must_use]
    pub const fn parse_statusword(statusword: u16) -> Cia402State {
        let bit0 = (statusword & (1 << 0)) != 0;
        let bit1 = (statusword & (1 << 1)) != 0;
        let bit2 = (statusword & (1 << 2)) != 0;
        let bit3 = (statusword & (1 << 3)) != 0;
        let bit5 = (statusword & (1 << 5)) != 0;
        let bit6 = (statusword & (1 << 6)) != 0;

        if bit3 {
            return Cia402State::Fault;
        }
        if !bit0 && !bit1 && !bit2 && !bit6 {
            return Cia402State::NotReadyToSwitchOn;
        }
        if bit6 && !bit0 && !bit1 && !bit2 {
            return Cia402State::SwitchOnDisabled;
        }
        if bit0 && !bit1 && !bit2 && !bit6 {
            return Cia402State::ReadyToSwitchOn;
        }
        if bit0 && bit1 && !bit2 && !bit6 {
            return Cia402State::SwitchedOn;
        }
        if bit0 && bit1 && bit2 && !bit6 {
            return Cia402State::OperationEnabled;
        }
        if bit0 && bit1 && !bit2 && bit5 {
            return Cia402State::QuickStopActive;
        }
        Cia402State::SwitchOnDisabled
    }

    #[must_use]
    pub fn transition_cia402(current: Cia402State, controlword: u16) -> Cia402State {
        let switch_on = (controlword & (1 << 0)) != 0;
        let enable_voltage = (controlword & (1 << 1)) != 0;
        let quick_stop = (controlword & (1 << 2)) != 0;
        let enable_op = (controlword & (1 << 3)) != 0;
        let fault_reset = (controlword & (1 << 7)) != 0;

        match current {
            Cia402State::Fault => {
                if fault_reset {
                    Cia402State::SwitchOnDisabled
                } else {
                    Cia402State::Fault
                }
            }
            Cia402State::SwitchOnDisabled => {
                if enable_voltage && quick_stop {
                    Cia402State::ReadyToSwitchOn
                } else {
                    Cia402State::SwitchOnDisabled
                }
            }
            Cia402State::ReadyToSwitchOn => {
                if !enable_voltage {
                    Cia402State::SwitchOnDisabled
                } else if switch_on && quick_stop {
                    Cia402State::SwitchedOn
                } else {
                    Cia402State::ReadyToSwitchOn
                }
            }
            Cia402State::SwitchedOn => {
                if !enable_voltage {
                    Cia402State::SwitchOnDisabled
                } else if !switch_on {
                    Cia402State::ReadyToSwitchOn
                } else if enable_op && quick_stop {
                    Cia402State::OperationEnabled
                } else {
                    Cia402State::SwitchedOn
                }
            }
            Cia402State::OperationEnabled => {
                if !enable_voltage {
                    Cia402State::SwitchOnDisabled
                } else if !quick_stop {
                    Cia402State::QuickStopActive
                } else if !enable_op {
                    Cia402State::SwitchedOn
                } else if !switch_on {
                    Cia402State::ReadyToSwitchOn
                } else {
                    Cia402State::OperationEnabled
                }
            }
            Cia402State::QuickStopActive => {
                if !enable_voltage {
                    Cia402State::SwitchOnDisabled
                } else if enable_op {
                    Cia402State::OperationEnabled
                } else {
                    Cia402State::QuickStopActive
                }
            }
            Cia402State::NotReadyToSwitchOn | Cia402State::FaultReactionActive => {
                Cia402State::SwitchOnDisabled
            }
        }
    }

    #[must_use]
    pub fn build_rpdo1_position(
        node_id: u8,
        target_pulse: i32,
        controlword: u16,
    ) -> CanOpenPdoFrame {
        let cob_id = 0x0200_u32 | u32::from(node_id);
        let mut data = [0_u8; 8];
        let cw_bytes = controlword.to_le_bytes();
        let pos_bytes = target_pulse.to_le_bytes();
        data[0] = cw_bytes[0];
        data[1] = cw_bytes[1];
        data[2] = pos_bytes[0];
        data[3] = pos_bytes[1];
        data[4] = pos_bytes[2];
        data[5] = pos_bytes[3];
        CanOpenPdoFrame {
            node_id,
            cob_id,
            data,
            len: 6,
            is_rx: true,
        }
    }

    pub fn parse_tpdo1_position(frame: &CanOpenPdoFrame) -> CortexResult<(u16, i32)> {
        if frame.len < 6 {
            return Err(CortexError::FieldbusFault);
        }
        let statusword = u16::from_le_bytes([frame.data[0], frame.data[1]]);
        let actual_pulse =
            i32::from_le_bytes([frame.data[2], frame.data[3], frame.data[4], frame.data[5]]);
        Ok((statusword, actual_pulse))
    }

    pub fn verify_ethercat_lrw(frame: &EtherCatLrwFrame) -> CortexResult<()> {
        if frame.working_counter != frame.expected_working_counter {
            return Err(CortexError::WorkingCounterMismatch);
        }
        Ok(())
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used, clippy::float_cmp)]
mod tests {
    use super::*;

    #[test]
    fn test_fieldbus_cia402_and_ethercat() {
        let cw_enable = FieldbusController::encode_controlword(true, true, true, true, false);
        let state1 =
            FieldbusController::transition_cia402(Cia402State::SwitchOnDisabled, cw_enable);
        assert_eq!(state1, Cia402State::ReadyToSwitchOn);

        let state2 = FieldbusController::transition_cia402(state1, cw_enable);
        assert_eq!(state2, Cia402State::SwitchedOn);

        let state3 = FieldbusController::transition_cia402(state2, cw_enable);
        assert_eq!(state3, Cia402State::OperationEnabled);

        let sw_op_enabled = 0x0027;
        let parsed_state = FieldbusController::parse_statusword(sw_op_enabled);
        assert_eq!(parsed_state, Cia402State::OperationEnabled);

        let rpdo = FieldbusController::build_rpdo1_position(3, 100_000, cw_enable);
        assert_eq!(rpdo.node_id, 3);
        assert_eq!(rpdo.cob_id, 0x203);

        let (sw, pos) = FieldbusController::parse_tpdo1_position(&rpdo).unwrap();
        assert_eq!(sw, cw_enable);
        assert_eq!(pos, 100_000);

        let ec_frame = EtherCatLrwFrame {
            logical_address: 0x10000,
            payload: vec![0x01, 0x02, 0x03, 0x04],
            working_counter: 3,
            expected_working_counter: 3,
        };
        assert!(FieldbusController::verify_ethercat_lrw(&ec_frame).is_ok());

        let ec_bad = EtherCatLrwFrame {
            logical_address: 0x10000,
            payload: vec![0x01, 0x02],
            working_counter: 2,
            expected_working_counter: 3,
        };
        assert!(FieldbusController::verify_ethercat_lrw(&ec_bad).is_err());
    }
}
