# =============================================================================
# TARJETA CRC - infra/helm/ragcorp/templates/_helpers.tpl
# =============================================================================
# Responsabilidades:
# - Definir helpers reutilizables para nombres y labels del chart.
# - Mantener consistencia entre recursos.
#
# Colaboradores:
# - templates/*.yaml
#
# Invariantes:
# - Nombres deterministas y estables para upgrades.
# =============================================================================

{{- define "ragcorp.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "ragcorp.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "ragcorp.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "ragcorp.componentName" -}}
{{- printf "%s-%s" (include "ragcorp.fullname" .root) .component | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "ragcorp.componentLabels" -}}
app.kubernetes.io/name: {{ include "ragcorp.name" .root }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{- define "ragcorp.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ragcorp.name" .root }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{- define "ragcorp.serviceAccountName" -}}
{{- if .serviceAccount.name -}}
{{- .serviceAccount.name -}}
{{- else -}}
{{- include "ragcorp.componentName" (dict "root" .root "component" .component) -}}
{{- end -}}
{{- end -}}
