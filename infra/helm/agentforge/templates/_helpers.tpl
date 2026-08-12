{{/*
Fully qualified name for a given service, e.g. "agentforge-api-gateway".
Kept short and predictable since docker-compose already uses bare service
names (api-gateway, agent-runtime, ...) for inter-service URLs in
values.yaml's `env` blocks — Kubernetes Service DNS names must match.
*/}}
{{- define "agentforge.serviceName" -}}
{{ .name }}
{{- end -}}

{{/*
Full image reference for a service: <registry>/<image>:<tag>, or just
<image>:<tag> if no registry is configured (e.g. local kind/minikube testing
with images loaded directly into the cluster).
*/}}
{{- define "agentforge.image" -}}
{{- $global := .global -}}
{{- $svc := .svc -}}
{{- if $global.imageRegistry -}}
{{ $global.imageRegistry }}/{{ $svc.image }}:{{ $global.imageTag }}
{{- else -}}
{{ $svc.image }}:{{ $global.imageTag }}
{{- end -}}
{{- end -}}

{{/*
Standard labels applied to every resource.
*/}}
{{- define "agentforge.labels" -}}
app.kubernetes.io/part-of: agentforge
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
