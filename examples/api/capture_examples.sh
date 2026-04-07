#!/bin/bash
# Activate your virtual environment before running this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIR="$SCRIPT_DIR"
API=http://localhost:8000

# Health
echo "-> health"
printf '$ curl -s %s/health | jq\n\n' "$API" > "$DIR/health.txt"
curl -s "$API/health" | jq . >> "$DIR/health.txt"

# Filter: clouds
echo "-> filter_clouds"
printf '$ curl -s -X POST %s/filters -H "Content-Type: application/json" -d '\''{"field": "cloud"}'\'' | jq\n\n' "$API" > "$DIR/filter_clouds.txt"
curl -s -X POST "$API/filters" -H "Content-Type: application/json" -d '{"field": "cloud"}' | jq . >> "$DIR/filter_clouds.txt"

# Filter: OS vendors
echo "-> filter_os_vendors"
printf '$ curl -s -X POST %s/filters -H "Content-Type: application/json" -d '\''{"field": "os_vendor"}'\'' | jq\n\n' "$API" > "$DIR/filter_os_vendors.txt"
curl -s -X POST "$API/filters" -H "Content-Type: application/json" -d '{"field": "os_vendor"}' | jq . >> "$DIR/filter_os_vendors.txt"

# Filter: OS versions for rhel
echo "-> filter_os_versions"
printf '$ curl -s -X POST %s/filters -H "Content-Type: application/json" -d '\''{"field": "os_version", "filters": {"os_vendor": "rhel"}}'\'' | jq\n\n' "$API" > "$DIR/filter_os_versions.txt"
curl -s -X POST "$API/filters" -H "Content-Type: application/json" -d '{"field": "os_version", "filters": {"os_vendor": "rhel"}}' | jq . >> "$DIR/filter_os_versions.txt"

# Filter: instances for azure rhel 9.6
echo "-> filter_instances"
printf '$ curl -s -X POST %s/filters -H "Content-Type: application/json" -d '\''{"field": "instance", "filters": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6"}}'\'' | jq\n\n' "$API" > "$DIR/filter_instances.txt"
curl -s -X POST "$API/filters" -H "Content-Type: application/json" -d '{"field": "instance", "filters": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6"}}' | jq . >> "$DIR/filter_instances.txt"

# Filter: benchmarks for azure rhel 9.6 D96
echo "-> filter_benchmarks"
printf '$ curl -s -X POST %s/filters -H "Content-Type: application/json" -d '\''{"field": "benchmark", "filters": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D96ds_v6"}}'\'' | jq\n\n' "$API" > "$DIR/filter_benchmarks.txt"
curl -s -X POST "$API/filters" -H "Content-Type: application/json" -d '{"field": "benchmark", "filters": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D96ds_v6"}}' | jq . >> "$DIR/filter_benchmarks.txt"

# Compare: passmark D96 vs D64 azure
echo "-> compare_passmark"
printf '$ curl -s -X POST %s/compare -H "Content-Type: application/json" -d '\''{"run1": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D96ds_v6", "benchmark": "passmark"}, "run2": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D64ds_v6", "benchmark": "passmark"}, "detail_level": "medium"}'\'' | jq\n\n' "$API" > "$DIR/compare_passmark.txt"
curl -s -X POST "$API/compare" -H "Content-Type: application/json" -d '{"run1": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D96ds_v6", "benchmark": "passmark"}, "run2": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D64ds_v6", "benchmark": "passmark"}, "detail_level": "medium"}' | jq . >> "$DIR/compare_passmark.txt"

# Ask: geomean math
echo "-> ask_geomean_math"
printf '$ curl -s -X POST %s/ask -H "Content-Type: application/json" -d '\''{"run1": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D96ds_v6", "benchmark": "passmark"}, "run2": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D64ds_v6", "benchmark": "passmark"}, "detail_level": "medium", "question": "Show me the math behind the geomean calculation"}'\'' | jq\n\n' "$API" > "$DIR/ask_geomean_math.txt"
curl -s -X POST "$API/ask" -H "Content-Type: application/json" -d '{"run1": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D96ds_v6", "benchmark": "passmark"}, "run2": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D64ds_v6", "benchmark": "passmark"}, "detail_level": "medium", "question": "Show me the math behind the geomean calculation"}' | jq . >> "$DIR/ask_geomean_math.txt"

echo ""
echo "Done! Files:"
ls -1 "$DIR"/*.txt
