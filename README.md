# remarcable-takehome-poc
This is a proof-of-concept project that demonstrates two things
* A dummy python service that logs using OpenTelemetry Protocol (OTLP) to show the structure and content of the logged data.
* Running a CI/CD pipeline where a CI test is run after every commit to the `main` branch. If the CI test passed, the a CD job is run which deploys a website to Github Pages.

## Example OTLP Logging Service

Requirements to run the service locally
- Python 3.10+

Steps to Run
```
# Activate venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run script
python example_service.py

## The script runs for approximately 6 seconds, to run 3 randomized dummy tasks
```
Example of an OTel Event fired by this script

```json
{
    "body": "Task 9032 successful",
    "severity_number": 9,
    "severity_text": "INFO",
    "attributes": {
        "task.id": 9032,
        "status": "done",
        "code.file.path": "<LOCAL_PROJECT_PATH>/remarcable-takehome-poc/test_service.py",
        "code.function.name": "perform_task",
        "code.line.number": 47
    },
    "dropped_attributes": 0,
    "timestamp": "2026-04-25T10:45:48.295212Z",
    "observed_timestamp": "2026-04-25T10:45:48.295284Z",
    "trace_id": "0x00000000000000000000000000000000",
    "span_id": "0x0000000000000000",
    "trace_flags": 0,
    "resource": {
        "attributes": {
            "telemetry.sdk.language": "python",
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.version": "1.41.1",
            "service.name": "compute-worker-service",
            "service.version": "1.0.0",
            "deployment.environment": "local-dev"
        },
        "schema_url": ""
    },
    "event_name": ""
}
```

Example of an uncaught exception OTel Event, created by adding a typo

```json
{
    "body": "Uncaught exception",
    "severity_number": 17,
    "severity_text": "ERROR",
    "attributes": {
        "code.file.path": "<LOCAL_PROJECT_PATH>/remarcable-takehome-poc/example_service.py",
        "code.function.name": "handle_exception",
        "code.line.number": 28,
        "exception.type": "AttributeError",
        "exception.message": "module 'time' has no attribute 'slep'",
        "exception.stacktrace": "Traceback (most recent call last):\n  File \"/Users/neelimnovo/projects/remarcable-takehome-poc/example_service.py\", line 84, in <module>\n    time.slep(2)\n    ^^^^^^^^^\nAttributeError: module 'time' has no attribute 'slep'. Did you mean: 'sleep'?\n"
    },
    "dropped_attributes": 0,
    "timestamp": "2026-04-25T14:55:41.035227Z",
    "observed_timestamp": "2026-04-25T14:55:41.035272Z",
    "trace_id": "0x00000000000000000000000000000000",
    "span_id": "0x0000000000000000",
    "trace_flags": 0,
    "resource": {
        "attributes": {
            "telemetry.sdk.language": "python",
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.version": "1.41.1",
            "service.name": "compute-worker-service",
            "service.version": "1.0.0",
            "deployment.environment": "local-dev"
        },
        "schema_url": ""
    },
    "event_name": ""
}



```

To run OTel logging hanlders in production in an EKS cluster, the following changes are required to the OTelService class in `example_service.py`

```
1) Replace ConsoleLogExporter with OTLPLogExporter.

2) Point the endpoint to your collector: e.g endpoint="http://otel-collector:4317".
```

To add a specific log file to the OTel Collector, the OTel Collector should run as a Daemonset (in the context of EKS). This makes one OTel Collector service run on each node. Make all services mount their log files to a specific file on the host node. After that, use the following ConfigMap to specific the log files which the OTel Collector should monitor and forward.

The recommened OTel Collector for EKS is AWS Distro for OpenTelemetry (ADOT). More details on ADOT documentation [here](https://github.com/aws-observability/aws-otel-collector), which supports Datadog as a backend to forward the OTel events to.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-config
data:
  agent.yaml: |
    receivers:
      filelog:
        include:
          - /var/log/<INSERT_EXAMPLE_LOG_FILE>.log
        start_at: beginning
    processors:
      attributes:
        actions:
          - key: container.name
            action: insert
            value: ${env:OTEL_RESOURCE_ATTRIBUTES_CONTAINER_NAME}
          - key: k8s.node.name
            action: insert
            value: ${env:OTEL_RESOURCE_ATTRIBUTES_K8S_NODE_NAME}
    service:
      pipelines:
        logs:
          receivers: [filelog]
          processors: [attributes]
          exporters: [otlp]
```

## CI/CD Example Pipeline

The CI/CD pipeline is defined in the `.github/workflows/ci-cd.yml` file. It performs the following steps:
1. CI: Runs a simple python compilation test on `example_service.py`. If it fails, the pipeline stops. If it passes, the pipeline continues to the CD stage.
2. CD: Runs `python example_service.py` and pipes its output to a code-formatted block in `public/index.html`. It then deploys the `public` folder to GitHub Pages.

You can check out the deployed website here:https://neelimnovo.github.io/ci-cd-OTLP-poc/

Given more time, I would have liked to test out using GitHub Actions to run a CI/CD pipeline in EKS for deployment, as well as Terraform IaC to for the cloud infrastructure.

## AI Usage Disclosure

This was made mostly using the Antigravity IDE, using the Gemini 3.1 Pro and Flash models, with some minor editing to the code.
AI Code output was verified manually by looking for the results I was expecting for the CI/CD deployment and code output. For the OTel productionizing advice, I cross-checked the documentation for AWS ADOT.

Main list of prompts used:

```
Generate code for a sample, dummy python service that performs its logging in an OpenTelemetry supported way. Give me details of how to launch this service to have this logging setup, and if I can test this locally
```

```
This will forward application emitted logs to my OTel collector. How can also I forward specific container logs also to the OTel collector? For example, if in my service has a log file called `/var/log/queue.log`, how can I forward that file to the OTel Collector?

Additionally, will this logging setup also send application errors to the OTel Collector?
```

```
Make a plan to create a dummy, proof-of-concept Github CI/CD pipeline using Github Actions. The pipeline should achieve the following
* On every commit, run a dummy CI test suite against the codebase.
* If the dummy CI test passes, run a dummy CD job
* The CD job can do something as simple as deploy a template website to a github pages website. It should try to do something whose dependencies are entirely self-contained within github and no other cloud platform
(If I need to register a github CI runner separately, let me know)
```

```
ci-cd.yml#L40-65
 Can you modify the deploy task such that:
* After checking out the code, it runs `python example_service.py` and pipes its output to a code-formatted block in index.html
So that when the deploy task deploys the index.html, it shows the output example_service.py
```
