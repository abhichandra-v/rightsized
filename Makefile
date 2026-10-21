# Rightsized end-to-end demo on kind.
#
#   make demo           full loop: cluster -> observe -> PR -> baseline -> apply -> candidate -> verify
#   make offline-demo   analyze/pr/compare on the bundled synthetic snapshot (no cluster needed)
#   make test           unit tests
#
# Needs: docker, kind, kubectl, helm, k6, python>=3.10. Full demo takes ~6h of wall clock
# (140 min observation + 3 baseline + 3 candidate + 3 VPA runs of 20 min each, plus settling).

SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c

BOUTIQUE_VERSION ?= v0.10.2
DAY_MINUTES      ?= 20
OBSERVE_DAYS     ?= 7
RUNS             ?= 3
NS               := boutique
export DAY_MINUTES RUNS

RS := rightsized
RESULTS := results

.PHONY: help install test offline-demo demo cluster monitoring vpa boutique-manifests boutique \
        forward unforward observe collect analyze pr reset apply baseline candidate verify \
        vpa-arm compare clean

help:
	@grep -E '^#   make' Makefile | sed 's/^#   //'

install:
	pip install -e '.[dev]'

test:
	python -m pytest -q

offline-demo:
	@mkdir -p $(RESULTS)/offline
	$(RS) -c examples/offline.yaml analyze examples/synthetic-snapshot.json --json $(RESULTS)/offline/summary.json
	@echo
	$(RS) -c examples/offline.yaml compare examples/synthetic-snapshot.json --vpa examples/synthetic-vpa.json

# ---------- cluster ----------

cluster:
	kind get clusters | grep -qx rightsized || kind create cluster --config deploy/kind/cluster.yaml

monitoring:
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null
	helm upgrade --install kps prometheus-community/kube-prometheus-stack -n monitoring --create-namespace \
	  -f deploy/monitoring/values.yaml --wait

vpa:
	helm repo add fairwinds-stable https://charts.fairwinds.com/stable >/dev/null
	helm upgrade --install vpa fairwinds-stable/vpa -n vpa --create-namespace \
	  --set updater.enabled=false --set admissionController.enabled=false --wait

boutique-manifests:
	@mkdir -p deploy/boutique/upstream
	curl -fsSL -o deploy/boutique/upstream/kubernetes-manifests.yaml \
	  https://raw.githubusercontent.com/GoogleCloudPlatform/microservices-demo/$(BOUTIQUE_VERSION)/release/kubernetes-manifests.yaml

boutique: boutique-manifests
	kubectl apply -k deploy/boutique
	kubectl apply -f deploy/vpa/vpa-objects.yaml
	kubectl -n $(NS) wait --for=condition=available deploy --all --timeout=10m

forward:
	@kubectl -n $(NS) port-forward svc/frontend 8080:80 >/dev/null 2>&1 & echo $$! > .pf-frontend
	@kubectl -n monitoring port-forward svc/kps-kube-prometheus-stack-prometheus 9090:9090 >/dev/null 2>&1 & echo $$! > .pf-prom
	@sleep 3

unforward:
	-@kill $$(cat .pf-frontend .pf-prom 2>/dev/null) 2>/dev/null; rm -f .pf-frontend .pf-prom

# ---------- observe -> recommend -> PR ----------

observe:
	RUNS=$(OBSERVE_DAYS) scripts/loadrun.sh observe

collect:
	$(RS) collect --out $(RESULTS)/snapshot.json
	kubectl get vpa -n $(NS) -o json > $(RESULTS)/vpa.json

analyze:
	$(RS) analyze $(RESULTS)/snapshot.json --json $(RESULTS)/analysis.json

# Writes the patch into deploy/boutique/resources.yaml and the PR body to results/.
# Add OPEN=1 to commit, push and open the PR with gh.
pr:
	$(RS) pr $(RESULTS)/snapshot.json --body-out $(RESULTS)/pr-body.md $(if $(OPEN),--open)

# ---------- closed-loop verification ----------

reset:
	cp deploy/boutique/resources.guessed.yaml deploy/boutique/resources.yaml

apply:
	kubectl apply -k deploy/boutique
	kubectl -n $(NS) rollout status deploy --timeout=10m
	sleep 120

baseline: reset apply
	scripts/loadrun.sh baseline

candidate: pr apply
	scripts/loadrun.sh candidate

# Exit 1 from verify = guardrail broken: restore the previous values and re-apply.
verify:
	$(RS) verify --out $(RESULTS)/verify-rightsized.md \
	  --baseline  $$(for i in $$(seq 1 $(RUNS)); do echo $(RESULTS)/baseline/run$$i.json:$(RESULTS)/baseline/run$$i.cluster.json; done) \
	  --candidate $$(for i in $$(seq 1 $(RUNS)); do echo $(RESULTS)/candidate/run$$i.json:$(RESULTS)/candidate/run$$i.cluster.json; done) \
	|| { echo "guardrail broken: rolling back"; $(MAKE) reset apply; exit 1; }

vpa-arm: reset
	$(RS) pr $(RESULTS)/snapshot.json --vpa $(RESULTS)/vpa.json --body-out $(RESULTS)/pr-body-vpa.md
	$(MAKE) apply
	scripts/loadrun.sh vpa
	-$(RS) verify --out $(RESULTS)/verify-vpa.md \
	  --baseline $$(for i in $$(seq 1 $(RUNS)); do echo $(RESULTS)/baseline/run$$i.json:$(RESULTS)/baseline/run$$i.cluster.json; done) \
	  --candidate $$(for i in $$(seq 1 $(RUNS)); do echo $(RESULTS)/vpa/run$$i.json:$(RESULTS)/vpa/run$$i.cluster.json; done)
	$(MAKE) reset apply

compare:
	$(RS) compare $(RESULTS)/snapshot.json --vpa $(RESULTS)/vpa.json | tee $(RESULTS)/compare.md

# A failed verify rolls back but must not stop the VPA arm: the comparison needs both.
demo: cluster monitoring vpa boutique forward observe collect analyze baseline candidate
	-$(MAKE) verify
	$(MAKE) vpa-arm compare
	@echo "Done. Everything is in $(RESULTS)/ ; commit it alongside the write-up."

clean: unforward
	kind delete cluster --name rightsized
