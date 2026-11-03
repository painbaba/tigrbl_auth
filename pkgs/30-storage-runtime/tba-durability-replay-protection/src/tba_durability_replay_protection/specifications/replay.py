"""Replay table alias and executable runtime specification."""

from tba_storage_replay_protection.tables import ReplayReservation

from tigrbl import deriveTableSpec
from tigrbl import makeOp
from tba_durability_replay_protection.operations.replay import check_and_reserve

ReplayReservationTable = ReplayReservation
ReplayReservationRuntimeSpec = deriveTableSpec(
    ReplayReservationTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="check_and_reserve",
            handler=check_and_reserve,
        ),
    ),
)

__all__ = ["ReplayReservationRuntimeSpec", "ReplayReservationTable"]
