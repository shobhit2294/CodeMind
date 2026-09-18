import pytest
from backend.execution.docker_runner import availability, run_tests
from backend.execution.sandbox import validate_changes, static_check
from backend.agents.verifier import verify
from backend.service import DEMO_FILES

@pytest.mark.skipif(not availability()['available'], reason='Docker and sandbox image required')
def test_real_docker_baseline_and_candidate():
    baseline=run_tests(DEMO_FILES)
    changed=DEMO_FILES['pricing.py'].replace('subtotal - discount_percent','subtotal * (1 - discount_percent / 100)')
    candidate=validate_changes(DEMO_FILES,{'pricing.py':changed})
    after=run_tests(candidate)
    assert baseline['counts']['failed']>0, baseline
    assert after['counts']['passed']==6, after
    assert verify(baseline,after,static_check(candidate),True)['verdict']=='verified'
