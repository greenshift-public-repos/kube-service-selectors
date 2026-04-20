Kubernetes services selectors exporter
====
Exports Kubernetes services selectors as Prometheus metrics.

Uses the Kubernetes API to collect service info and converts selector labels to Prometheus-compatible label names.

[Source Code](https://github.com/greenshift-public-repos/kube-service-selectors) | [Helm chart](https://github.com/greenshift-public-repos/helm-charts/tree/main/charts/kube-service-selectors)

## Metrics

| Metric name | Metric type | Description | Labels |
| ----------- | ----------- | ----------- | ------ |
| `kube_service_selectors` | Gauge | Kubernetes service selectors converted to Prometheus labels | `service`=&lt;service-name&gt; `namespace`=&lt;service-namespace&gt; `uid`=&lt;service-uid&gt; `label_SELECTOR_LABEL`=&lt;value&gt; |
| `kube_service_selectors_total` | Counter | Exporter workflow result per collection cycle | `result`=`succeeded`\|`failed` |

Selector label keys are normalised to [Prometheus label naming conventions](https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels) (snake\_case, non-alphanumeric characters replaced with `_`) and conflicts are resolved the same way as [kube-state-metrics](https://github.com/kubernetes/kube-state-metrics/blob/master/README.md#conflict-resolution-in-label-names) — by appending a `_conflictN` suffix.

## Usage

```
usage: main.py [-h] [--port PORT] [--namespaces NAMESPACES] [--debug DEBUG]
               [--timeout TIMEOUT] [--kubeconfig KUBECONFIG]

options:
  -h, --help            show this help message and exit
  --port PORT           server port (default: 30091)
  --namespaces NAMESPACES
                        comma-separated list of namespaces to watch
                        (all namespaces if not provided)
  --debug DEBUG         enable debug logging
  --timeout TIMEOUT     Kubernetes API request timeout in seconds (default: 10)
  --kubeconfig KUBECONFIG
                        path to kubeconfig file; in-cluster service account
                        credentials are used if the file is not found
```

## CI/CD

PRs run tests (black, pycodestyle, pytest) via Docker. Merges to `main` and `v*` tags additionally build and push the image to ACR, tagged with the short commit SHA. Version tags also push the image tagged with the version number.

Requires the following configured on the GitHub repo:
- **Secret** `AZURE_CREDENTIALS` — service principal JSON with `AcrPush` on the ACR
- **Variable** `ACR_NAME` — registry name (without `.azurecr.io`)

### From source

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python -m kube_service_selectors.main --kubeconfig <kubeconfig_path>
```

By default the server listens on port **30091**. When running outside a cluster, pass a kubeconfig via `--kubeconfig`. Inside a cluster, omit it and the pod's service account credentials are used automatically.

### Using Docker

```bash
docker run -d \
  -v <kubeconfig_path>:/usr/src/app/kube_service_selectors/kubeconfig \
  -p 30091:30091 \
  --name kss_exporter \
  greenshift/kube-service-selectors
```

To target specific namespaces:

```bash
docker run -d \
  -v <kubeconfig_path>:/usr/src/app/kube_service_selectors/kubeconfig \
  -p 30091:30091 \
  --name kss_exporter \
  greenshift/kube-service-selectors --namespaces default,kube-system
```
