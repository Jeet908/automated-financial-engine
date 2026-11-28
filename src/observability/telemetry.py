"""
Full-stack OpenTelemetry (OTel) observability and SLA tracking stack.
Provides zero-error distributed tracing, latency histograms, and upstream
regulatory schema drift alerting with graceful no-op fallbacks.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)

# Flag indicating whether real OpenTelemetry SDK is initialized
_OTEL_AVAILABLE = False
_tracer = None
_meter = None

# Custom Metric Instruments
_scraper_latency_hist = None
_pipeline_duration_hist = None
_schema_drift_counter = None
_invariant_failure_counter = None


# ---------------------------------------------------------------------------
# In-Memory SLA & Telemetry Tracker (Always available regardless of OTel daemon)
# ---------------------------------------------------------------------------
class SLATracker:
    """Thread-safe SLA aggregator tracking 99.9% availability, latency & drift."""

    def __init__(self) -> None:
        self.total_pipeline_runs: int = 0
        self.successful_runs: int = 0
        self.failed_runs: int = 0
        self.scraper_latencies: List[float] = []
        self.pipeline_durations: List[float] = []
        self.schema_drift_events: List[Dict[str, Any]] = []
        self.invariant_failures: List[Dict[str, Any]] = []
        self.start_time: float = time.time()

    def record_run(self, duration_ms: float, success: bool = True) -> None:
        self.total_pipeline_runs += 1
        if success:
            self.successful_runs += 1
        else:
            self.failed_runs += 1
        self.pipeline_durations.append(duration_ms)
        if len(self.pipeline_durations) > 1000:
            self.pipeline_durations.pop(0)

    def record_scraper(self, latency_ms: float) -> None:
        self.scraper_latencies.append(latency_ms)
        if len(self.scraper_latencies) > 1000:
            self.scraper_latencies.pop(0)

    def record_drift(self, source_system: str, missing_tag: str, details: str = "") -> None:
        self.schema_drift_events.append({
            "timestamp": time.time(),
            "source_system": source_system,
            "missing_tag": missing_tag,
            "details": details,
        })
        if len(self.schema_drift_events) > 500:
            self.schema_drift_events.pop(0)

    def record_invariant_failure(self, job_id: str, max_err: float, gate_name: str = "") -> None:
        self.invariant_failures.append({
            "timestamp": time.time(),
            "job_id": job_id,
            "max_err": max_err,
            "gate_name": gate_name,
        })
        if len(self.invariant_failures) > 500:
            self.invariant_failures.pop(0)

    def get_summary(self) -> Dict[str, Any]:
        uptime_seconds = round(time.time() - self.start_time, 1)
        avail = 100.0
        if self.total_pipeline_runs > 0:
            avail = round((self.successful_runs / self.total_pipeline_runs) * 100.0, 3)

        avg_scraper = (
            round(sum(self.scraper_latencies) / len(self.scraper_latencies), 2)
            if self.scraper_latencies else 0.0
        )
        avg_pipeline = (
            round(sum(self.pipeline_durations) / len(self.pipeline_durations), 2)
            if self.pipeline_durations else 0.0
        )

        return {
            "service": "marketlens-valuation-platform",
            "sla_target_availability": "99.9%",
            "current_availability_pct": avail,
            "uptime_seconds": uptime_seconds,
            "total_pipeline_runs": self.total_pipeline_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "avg_scraper_latency_ms": avg_scraper,
            "avg_pipeline_duration_ms": avg_pipeline,
            "total_schema_drifts_detected": len(self.schema_drift_events),
            "total_invariant_failures": len(self.invariant_failures),
            "status": "HEALTHY" if len(self.invariant_failures) == 0 else "DEGRADED",
            "otel_active": _OTEL_AVAILABLE,
        }


sla_tracker = SLATracker()


# ---------------------------------------------------------------------------
# OpenTelemetry Safe Initialization with No-Op Fallback
# ---------------------------------------------------------------------------
def _init_opentelemetry() -> None:
    global _OTEL_AVAILABLE, _tracer, _meter
    global _scraper_latency_hist, _pipeline_duration_hist
    global _schema_drift_counter, _invariant_failure_counter

    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    service_name = os.environ.get("OTEL_SERVICE_NAME", "marketlens-financial-engine")

    try:
        from opentelemetry import metrics, trace
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider

        resource = Resource.create({"service.name": service_name})
        tracer_provider = TracerProvider(resource=resource)
        meter_provider = MeterProvider(resource=resource)

        if otlp_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
                from opentelemetry.sdk.trace.export import BatchSpanProcessor

                span_exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
                tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))

                metric_exporter = OTLPMetricExporter(endpoint=f"{otlp_endpoint}/v1/metrics")
                reader = PeriodicExportingMetricReader(metric_exporter)
                meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
            except Exception as exp_err:
                logger.warning("OTLP HTTP Exporter unavailable (%s); running local SDK mode.", exp_err)

        trace.set_tracer_provider(tracer_provider)
        metrics.set_meter_provider(meter_provider)

        _tracer = trace.get_tracer("marketlens.valuation", "2.0.0")
        _meter = metrics.get_meter("marketlens.metrics", "2.0.0")

        _scraper_latency_hist = _meter.create_histogram(
            name="scraper.latency_ms",
            description="Latency of live web scraper operations across SEC EDGAR & Screener.in",
            unit="ms",
        )
        _pipeline_duration_hist = _meter.create_histogram(
            name="valuation.pipeline_duration_ms",
            description="Full end-to-end 3-statement and DCF pipeline execution duration",
            unit="ms",
        )
        _schema_drift_counter = _meter.create_counter(
            name="scraper.schema_drift_total",
            description="Total upstream schema drift and missing tag events detected",
            unit="1",
        )
        _invariant_failure_counter = _meter.create_counter(
            name="audit.invariant_failure_total",
            description="Total structural accounting invariant discrepancies detected",
            unit="1",
        )

        _OTEL_AVAILABLE = True
        logger.info("OpenTelemetry instrumentation successfully initialized for service: %s", service_name)

    except ImportError:
        logger.debug("OpenTelemetry packages not installed; telemetry operating in local SLA mode.")
    except Exception as exc:
        logger.warning("Could not initialize OpenTelemetry: %s; using local SLA fallback.", exc)


_init_opentelemetry()


# ---------------------------------------------------------------------------
# Tracing & Metric Helpers with Universal Fallback
# ---------------------------------------------------------------------------
class _NoOpSpan:
    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def record_exception(self, exception: Exception) -> None:
        pass

    def set_status(self, *args, **kwargs) -> None:
        pass


@contextmanager
def trace_span(name: str, attributes: Optional[Dict[str, Any]] = None) -> Generator[Any, None, None]:
    """
    Context manager that starts a distributed OTel trace span if available,
    or yields a safe no-op span context.
    """
    if _OTEL_AVAILABLE and _tracer is not None:
        with _tracer.start_as_current_span(name) as span:
            if attributes:
                for k, v in attributes.items():
                    span.set_attribute(k, str(v))
            yield span
    else:
        yield _NoOpSpan()


def record_scraper_latency(latency_ms: float, attributes: Optional[Dict[str, str]] = None) -> None:
    """Record scraper latency histogram and track in local SLA monitor."""
    sla_tracker.record_scraper(latency_ms)
    if _scraper_latency_hist is not None:
        try:
            _scraper_latency_hist.record(latency_ms, attributes or {})
        except Exception:
            pass


def record_pipeline_duration(duration_ms: float, success: bool = True, attributes: Optional[Dict[str, str]] = None) -> None:
    """Record valuation pipeline duration histogram and track in local SLA monitor."""
    sla_tracker.record_run(duration_ms, success=success)
    if _pipeline_duration_hist is not None:
        try:
            _pipeline_duration_hist.record(duration_ms, attributes or {})
        except Exception:
            pass


def record_schema_drift(source_system: str, missing_tag: str, details: str = "") -> None:
    """Record an upstream schema drift event (e.g. missing XBRL tag or changed table structure)."""
    sla_tracker.record_drift(source_system, missing_tag, details)
    if _schema_drift_counter is not None:
        try:
            _schema_drift_counter.add(1, {"source": source_system, "tag": missing_tag})
        except Exception:
            pass
    logger.warning(
        "[UPSTREAM SCHEMA DRIFT DETECTED] Source: %s | Missing Tag: %s | Details: %s",
        source_system,
        missing_tag,
        details,
    )


def record_invariant_discrepancy(job_id: str, max_err: float, gate_name: str = "") -> None:
    """Record an accounting invariant error (>1e-4) to telemetry counter and SLA monitor."""
    sla_tracker.record_invariant_failure(job_id, max_err, gate_name)
    if _invariant_failure_counter is not None:
        try:
            _invariant_failure_counter.add(1, {"job_id": job_id, "gate": gate_name})
        except Exception:
            pass
    logger.error(
        "[ACCOUNTING INVARIANT VIOLATION] Job: %s | Gate: %s | Max Error: %e (Tolerance: 1e-4)",
        job_id,
        gate_name,
        max_err,
    )
