from server.core.decision.decision_engine import decision_engine
from server.core.kernel.consensus.ballot import Ballot
from server.core.kernel.consensus.critical import CriticalAction
from server.core.kernel.domain.dag import ExecutionDag

_CATASTROPHIC_TOKENS = ("formatta", "rm -rf", "drop table", "cancella chiavi", "wipe")


class ProbabilisticGuardrailVoter:
    name = "probabilistic_guardrail"
    can_veto = False

    def __init__(self, action: CriticalAction) -> None:
        self._action = action

    async def vote(self, dag: ExecutionDag) -> Ballot:
        utt_lower = self._action.utterance.lower()
        catastrophic = any(tok in utt_lower for tok in _CATASTROPHIC_TOKENS)
        out = decision_engine.decide_verdict(
            proposition="The requested tool execution is safe to run without additional destructive confirmation.",
            state={
                "command": self._action.utterance,
                "destructive": catastrophic,
                "authenticated": not catastrophic,
                "domain": self._action.domain,
                "service": self._action.service,
            },
        )
        if out.abstained:
            return Ballot(
                self.name,
                True,
                f"abstention_band_caution (p_yes={out.expected_value:.2f}, conf={out.confidence:.2f})",
            )
        approved = out.predicted_label == "yes"
        return Ballot(
            self.name,
            approved,
            f"verdict={out.predicted_label} (p_yes={out.expected_value:.2f}, conf={out.confidence:.2f})",
        )
