import sys
import logging
import time
import random
from opentelemetry import _logs
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk.resources import Resource

# --- OTel Setup ---

class OTelService:
    """Inheritable class that automatically sets up OpenTelemetry logging."""
    _otel_initialized = False
    logger_provider = None

    def __init__(self):
        self._init_otel()
        # Automatically create a logger named after the child class
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        sys.excepthook = self.handle_exception
    
    def handle_exception(self,exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        self.logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    @classmethod
    def _init_otel(cls):
        if not OTelService._otel_initialized:
            # 1. Define who this service is
            resource = Resource.create({
                "service.name": "compute-worker-service",
                "service.version": "1.0.0",
                "deployment.environment": "local-dev"
            })
            
            # 2. Setup the Logger Provider
            provider = LoggerProvider(resource=resource)
            _logs.set_logger_provider(provider)
            
            # 3. Choose where to send logs. 
            # Locally, we'll print to the Console in OTel format.
            # For production, you'd swap ConsoleLogExporter for OTLPLogExporter.
            exporter = ConsoleLogExporter()
            provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
            
            # 4. Connect OTel to Python's standard logging module
            handler = LoggingHandler(level=logging.INFO, logger_provider=provider)
            logging.getLogger().addHandler(handler)
            
            OTelService.logger_provider = provider
            OTelService._otel_initialized = True

    @classmethod
    def shutdown_otel(cls):
        if cls.logger_provider:
            cls.logger_provider.shutdown()


# --- Service Logic ---

class WorkerService(OTelService):
    def perform_task(self, task_id):
        # Adding 'extra' data attaches OTel attributes to the log record
        self.logger.info(f"Starting task {task_id}", extra={"task.id": task_id, "priority": "high"})
        
        time.sleep(random.uniform(0.5, 1.5))
        
        if random.random() > 0.8:
            self.logger.error(f"Task {task_id} failed!", extra={"task.id": task_id, "error_code": 500})
        else:
            self.logger.info(f"Task {task_id} successful", extra={"task.id": task_id, "status": "done"})

if __name__ == "__main__":
    print("Service started. Press Ctrl+C to stop.\n")
    worker = WorkerService()
    try:
        while True:
            job_id = random.randint(1000, 9999)
            worker.perform_task(job_id)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nShutting down...")
        OTelService.shutdown_otel()