from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from tools.validate_cqc_resume_lineage import validate_source_run


RUN = {"repository": {"full_name": "owner/caregist"}, "head_branch": "main",
       "path": ".github/workflows/cqc-reconciliation.yml", "status": "completed",
       "head_sha": "a" * 40, "conclusion": "failure"}


def test_completed_failed_run_can_reach_the_database_resume_guards():
    validate_source_run(RUN, repository="owner/caregist", release_sha="a" * 40)


@pytest.mark.parametrize("field,value", [
    ("head_sha", "b" * 40), ("head_branch", "feature/other"),
    ("status", "in_progress"), ("path", ".github/workflows/other.yml"),
    ("repository", {"full_name": "other/caregist"}),
])
def test_invalid_lineage_is_refused(field, value):
    run = deepcopy(RUN)
    run[field] = value
    with pytest.raises(ValueError):
        validate_source_run(run, repository="owner/caregist", release_sha="a" * 40)


def test_preflight_precedes_manifest_upload_and_resume():
    workflow = yaml.load(Path(".github/workflows/cqc-reconciliation.yml").read_text(),
                         Loader=yaml.BaseLoader)
    steps = workflow["jobs"]["prepare"]["steps"]
    gate = next(i for i, step in enumerate(steps)
                if step.get("name") == "Validate resume source lineage before database writes")
    download = next(i for i, step in enumerate(steps)
                    if step.get("name") == "Download the original immutable manifest")
    resume = next(i for i, step in enumerate(steps) if step.get("id") == "resume")
    assert gate < download < resume
    assert steps[gate]["if"] == "steps.batch.outputs.resume == 'true'"
    assert "DATABASE_URL" not in steps[gate]["env"]
