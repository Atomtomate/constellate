import datetime as dt

from constellate.models import RunOutcome
from constellate.repos import sources
from factories import OWNER, T0, make_run, make_source


def test_get_or_create_source_creates_once_and_stamps_the_owner(session):
    first = sources.get_or_create_source(session, owner_id=OWNER, key="lastfm", service="spotify")
    second = sources.get_or_create_source(session, owner_id=OWNER, key="lastfm", service="spotify")
    assert first.id == second.id
    assert first.owner_id == OWNER
    assert first.cursor is None


def test_set_cursor_replaces_it_wholesale(session):
    source = make_source(session)
    sources.set_cursor(session, source, {"from": 1})
    sources.set_cursor(session, source, {"until": 2})
    session.expire_all()
    assert source.cursor == {"until": 2}


def test_start_run_opens_a_run_with_no_outcome(session):
    source = make_source(session)
    run = sources.start_run(session, source, owner_id=OWNER, started_at=T0, file_sha256="ab")
    assert (run.source_id, run.owner_id, run.outcome, run.file_sha256) == (
        source.id,
        OWNER,
        None,
        "ab",
    )


def test_finish_run_records_outcome_counts_and_error(session):
    run = make_run(session)
    end = T0 + dt.timedelta(minutes=1)
    sources.finish_run(
        session, run, finished_at=end, outcome=RunOutcome.FAILED, counts={"new": 3}, error="boom"
    )
    session.expire_all()
    assert (run.finished_at, run.outcome, run.counts, run.error) == (
        end,
        "failed",
        {"new": 3},
        "boom",
    )


def test_find_ok_run_by_hash_ignores_failed_runs_and_other_files(session):
    source = make_source(session)
    make_run(session, source_id=source.id, file_sha256="ab", outcome="failed")
    make_run(session, source_id=source.id, file_sha256="cd", outcome="ok")
    assert sources.find_ok_run_by_hash(session, source.id, "ab") is None
    ok = make_run(session, source_id=source.id, file_sha256="ab", outcome="ok")
    assert sources.find_ok_run_by_hash(session, source.id, "ab").id == ok.id


def test_find_ok_run_by_hash_is_per_source(session):
    run = make_run(session, file_sha256="ab", outcome="ok")
    assert sources.find_ok_run_by_hash(session, make_source(session).id, "ab") is None
    assert sources.find_ok_run_by_hash(session, run.source_id, "ab").id == run.id
