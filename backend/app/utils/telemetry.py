from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def setup_telemetry(app):
    """
    Configures OpenTelemetry for the application.
    Exports traces to Console (for dev) and OTLP (if configured).
    """
    resource = Resource.create(attributes={
        "service.name": settings.OTEL_SERVICE_NAME,
        "service.version": "1.0.0"
    })

    provider = TracerProvider(resource=resource)

    # 1. Console Exporter (for detailed debugging in logs)
    # console_exporter = ConsoleSpanExporter()
    # provider.add_span_processor(BatchSpanProcessor(console_exporter))

    # 2. OTLP Exporter (for Jaeger, Zipkin, Datadog etc.)
    # Only add if an endpoint is provided, otherwise it might error out or log warnings
    otlp_endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT
    if otlp_endpoint:
        logger.info(f"Setting up OTLP Exporter to {otlp_endpoint}")
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    else:
        logger.info("No OTEL_EXPORTER_OTLP_ENDPOINT set. defaulting to console if needed or no-op.")
        # fallback to console if no OTLP, so we can see something
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    
    logger.info("OpenTelemetry setup complete.")
