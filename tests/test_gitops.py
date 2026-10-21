import pytest
from conftest import MI, make_ev
from ruamel.yaml import YAML

from rightsized.gitops import patch_helm_values, patch_manifest
from rightsized.models import Recommendation, Resources

MANIFEST = """\
# guessed values
apiVersion: v1
kind: Service
metadata:
  name: web
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  template:
    spec:
      containers:
        - name: app  # main
          image: example/app:1
          resources:
            requests: { cpu: "1", memory: 1Gi }
            limits: { cpu: "2", memory: 2Gi }
        - name: sidecar
          image: example/sidecar:1
"""

VALUES = """\
web:
  image: example/app
  # tuned by hand in 2023
  resources:
    requests:
      cpu: "1"
      memory: 1Gi
"""


def load_all(text):
    return list(YAML(typ="safe").load_all(text))


def rec():
    return Recommendation(evidence=make_ev(), requests=Resources(cpu=0.23, memory=512 * MI),
                          limits=Resources(cpu=2.0, memory=2048 * MI))


def test_patch_manifest_changes_only_the_target_container():
    out = patch_manifest(MANIFEST, "shop", "web", "app", rec())
    svc, deploy = load_all(out)
    app, sidecar = deploy["spec"]["template"]["spec"]["containers"]
    assert app["resources"] == {"requests": {"cpu": "230m", "memory": "512Mi"},
                                "limits": {"cpu": "2", "memory": "2Gi"}}
    assert "resources" not in sidecar
    assert svc["kind"] == "Service"
    assert "# guessed values" in out and "# main" in out


def test_patch_manifest_unknown_container_raises():
    with pytest.raises(KeyError):
        patch_manifest(MANIFEST, "shop", "web", "nope", rec())


def test_patch_helm_values_keeps_comments_and_does_not_invent_limits():
    out = patch_helm_values(VALUES, "web.resources", rec())
    assert "# tuned by hand in 2023" in out
    assert load_all(out)[0]["web"]["resources"] == {"requests": {"cpu": "230m", "memory": "512Mi"}}
