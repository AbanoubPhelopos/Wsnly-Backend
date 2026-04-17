import logging
import threading
from django.conf import settings

logger = logging.getLogger(__name__)


_ai_client = None
_routing_client = None
_ai_lock = threading.Lock()
_routing_lock = threading.Lock()
_init_errors = {}


def _init_ai_client():
    from src.Infrastructure.GrpcClients.ai_client import AiGrpcClient

    global _ai_client
    if _ai_client is not None:
        return
    try:
        _ai_client = AiGrpcClient(
            host=settings.AI_GRPC_HOST,
            port=settings.AI_GRPC_PORT,
            timeout_seconds=settings.AI_GRPC_TIMEOUT_SECONDS,
        )
        logger.info(
            "AI gRPC client initialized",
            extra={
                "extra_fields": {
                    "host": settings.AI_GRPC_HOST,
                    "port": settings.AI_GRPC_PORT,
                }
            },
        )
    except RuntimeError as exc:
        _init_errors["ai"] = str(exc)
        logger.error(
            "AI gRPC client initialization failed",
            extra={"extra_fields": {"error": str(exc)}},
        )


def _init_routing_client():
    from src.Infrastructure.GrpcClients.routing_client import RoutingGrpcClient

    global _routing_client
    if _routing_client is not None:
        return
    try:
        _routing_client = RoutingGrpcClient(
            host=settings.ROUTING_GRPC_HOST,
            port=settings.ROUTING_GRPC_PORT,
            timeout_seconds=settings.ROUTING_GRPC_TIMEOUT_SECONDS,
        )
        logger.info(
            "Routing gRPC client initialized",
            extra={
                "extra_fields": {
                    "host": settings.ROUTING_GRPC_HOST,
                    "port": settings.ROUTING_GRPC_PORT,
                }
            },
        )
    except RuntimeError as exc:
        _init_errors["routing"] = str(exc)
        logger.error(
            "Routing gRPC client initialization failed",
            extra={"extra_fields": {"error": str(exc)}},
        )


def get_ai_client():
    with _ai_lock:
        if _ai_client is None and "ai" not in _init_errors:
            _init_ai_client()
        return _ai_client, _init_errors.get("ai")


def get_routing_client():
    with _routing_lock:
        if _routing_client is None and "routing" not in _init_errors:
            _init_routing_client()
        return _routing_client, _init_errors.get("routing")


def reset():
    global _ai_client, _routing_client, _init_errors
    _ai_client = None
    _routing_client = None
    _init_errors = {}
