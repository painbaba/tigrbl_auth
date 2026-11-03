"""Security-event table aliases and executable runtime specifications."""

from tba_storage_security_event.tables import SecurityEvent, SecurityEventDelivery, SecurityEventReplay, SecurityEventSubscription

from tigrbl import deriveTableSpec
from tigrbl import makeOp
from tba_durability_security_event.operations.security_events import (
    enqueue_security_event_delivery,
    record_security_event,
    record_security_event_subscription,
    reserve_security_event_replay,
)

SecurityEventTable = SecurityEvent
SecurityEventDeliveryTable = SecurityEventDelivery
SecurityEventReplayTable = SecurityEventReplay
SecurityEventSubscriptionTable = SecurityEventSubscription

SecurityEventRuntimeSpec = deriveTableSpec(
    SecurityEventTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="record_event",
            handler=record_security_event,
        ),
    ),
)
SecurityEventDeliveryRuntimeSpec = deriveTableSpec(
    SecurityEventDeliveryTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="enqueue_delivery",
            handler=enqueue_security_event_delivery,
        ),
    ),
)
SecurityEventSubscriptionRuntimeSpec = deriveTableSpec(
    SecurityEventSubscriptionTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="record_subscription",
            handler=record_security_event_subscription,
        ),
    ),
)
SecurityEventReplayRuntimeSpec = deriveTableSpec(
    SecurityEventReplayTable,
    ops=(
        makeOp(
            extra={"owner_layer": "30-storage-runtime"},
            expose_routes=False,
            expose_rpc=False,
            expose_method=True,
            tx_scope="read_write",
            alias="reserve_replay",
            handler=reserve_security_event_replay,
        ),
    ),
)

__all__ = [
    "SecurityEventDeliveryRuntimeSpec",
    "SecurityEventDeliveryTable",
    "SecurityEventReplayRuntimeSpec",
    "SecurityEventReplayTable",
    "SecurityEventRuntimeSpec",
    "SecurityEventTable",
    "SecurityEventSubscriptionRuntimeSpec",
    "SecurityEventSubscriptionTable",
]
