import json
from pathlib import Path

import pytest
from django.core.cache import cache
from django.core.management import CommandError, call_command

from main.debut_io import DebutDocumentError, import_debuts
from main.models import Artist

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "artist_debuts.json"


def document(*entries):
    return {
        "version": 1,
        "debuts": [
            {"artist": slug, "debut": debut, "source": "Wikipedia: test"}
            for slug, debut in entries
        ],
    }


@pytest.mark.django_db
def test_import_makes_debuts_match_the_file_and_withdraws_omitted_entries():
    riize = Artist.objects.create(name="Riize")
    exo = Artist.objects.create(name="Exo")

    assert import_debuts(document(("riize", "2023-09-04"), ("exo", "2012"))) == 2
    assert import_debuts(document(("riize", "2023-09-04"), ("exo", "2012"))) == 0
    assert import_debuts(document(("riize", "2023-09-04")), dry_run=True) == 1
    exo.refresh_from_db()
    assert exo.debut == "2012"

    assert import_debuts(document(("riize", "2023-09-04"))) == 1
    exo.refresh_from_db()
    riize.refresh_from_db()
    assert (riize.debut, exo.debut) == ("2023-09-04", "")

    solo = document(("riize", "2023-09-04"))
    solo["debuts"][0]["solo"] = True
    assert import_debuts(solo) == 1
    riize.refresh_from_db()
    assert riize.debut_solo is True
    assert import_debuts(document(("riize", "2023-09-04"))) == 1
    riize.refresh_from_db()
    assert riize.debut_solo is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    "debut", ["2023-9-04", "2023-02-30", "2023-13", "1900", "2999", 2023, "23"]
)
def test_import_rejects_invalid_debuts_before_writing(debut):
    Artist.objects.create(name="Riize")
    with pytest.raises(DebutDocumentError):
        import_debuts(document(("riize", debut)))
    assert Artist.objects.get().debut == ""


@pytest.mark.django_db
def test_import_rejects_unknown_and_duplicate_artists():
    Artist.objects.create(name="Riize")
    with pytest.raises(DebutDocumentError, match="Unknown artist slug"):
        import_debuts(document(("riize", "2023"), ("merged-away", "2020")))
    solo = document(("riize", "2023"))
    solo["debuts"][0]["solo"] = False
    with pytest.raises(DebutDocumentError, match="solo"):
        import_debuts(solo)
    with pytest.raises(DebutDocumentError, match="duplicate"):
        import_debuts(document(("riize", "2023"), ("riize", "2023-09")))


@pytest.mark.django_db
def test_command_reports_document_errors(tmp_path):
    path = tmp_path / "debuts.json"
    path.write_text(json.dumps({"version": 2, "debuts": []}), encoding="utf-8")
    with pytest.raises(CommandError, match="version 1"):
        call_command("import_artist_debuts", str(path))


def test_shipped_debuts_file_is_valid():
    from main.debut_io import _validate

    debuts = _validate(json.loads(DATA_FILE.read_text(encoding="utf-8")))
    assert debuts["riize"] == ("2023-09-04", False)
    assert debuts["jennie"] == ("2018-11-12", True)


@pytest.mark.django_db
def test_artist_detail_exposes_debut(client):
    Artist.objects.create(name="Riize")
    import_debuts(document(("riize", "2023-09-04")))
    response = client.get("/api/v1/artists/riize")
    # Leave the shared anonymous throttle budget to the API suite.
    cache.clear()
    assert (response.data["debut"], response.data["debut_solo"]) == (
        "2023-09-04",
        False,
    )
