import pytest

from journal.config import Config
from journal.features.secrets.support.secret_run import SecretRun
from journal.models.secret import Secret
from journal.support.masks import Masks
from journal.support.rejection import Rejection
from journal.support.secret_field import SecretField
from journal.support.secret_values import SecretValues

KEY = "ghp_0123456789abcdef"


@pytest.fixture
def values(tmp_path, monkeypatch) -> SecretValues:
    monkeypatch.setenv("AGENT_JOURNAL_SECRETS", str(tmp_path / "private"))
    return SecretValues(Config(tmp_path))


def test_a_common_word_or_a_word_of_a_secrets_own_name_is_never_masked_and_a_real_value_is(values: SecretValues):
    values.write({"STAGING_LOGIN_PASSWORD": "password", "STAGING_TRANSPORTKLOK_KEY": "transportklok", "GITHUB_KEY": KEY})
    masks = Masks(values)
    text = "secret 12's field password of the transportklok login, key " + KEY
    assert masks.masked((text,)) == ("secret 12's field password of the transportklok login, key [secret GITHUB_KEY]",)
    assert [variable for variable, _ in masks.leaks] == ["GITHUB_KEY"]


def test_a_value_written_as_a_placeholder_stays_as_it_is_and_is_no_leak(values: SecretValues):
    values.write({"GITHUB_KEY": KEY})
    masks = Masks(values)
    command = f"journal secret run 12 --stdin {{{KEY}}}"
    assert masks.masked((command,)) == (command,) and not masks.has_secret((command,)) and masks.leaks == []
    assert masks.masked((f"{{{KEY}}} and {KEY}",)) == (f"{{{KEY}}} and [secret GITHUB_KEY]",) and masks.has_secret((KEY,))


def test_a_hidden_value_that_is_a_common_word_or_part_of_its_name_is_refused_at_store_time_and_a_shown_one_is_stored(values: SecretValues):
    with pytest.raises(Rejection, match="common word"):
        values.put_field(SecretField("password", True, "STAGING_LOGIN_PASSWORD"), "password")
    with pytest.raises(Rejection, match="common word"):
        values.put_field(SecretField("key", True, "STAGING_TRANSPORTKLOK_KEY"), "Transportklok")
    values.put_field(SecretField("username", False, "STAGING_LOGIN_USERNAME"), "username")
    values.put_field(SecretField("key", True, "GITHUB_KEY"), KEY)
    assert values.values() == {"STAGING_LOGIN_USERNAME": "username", "GITHUB_KEY": KEY}


def test_a_secrets_replaced_values_are_forgotten_and_its_current_value_kept(values: SecretValues):
    values.put("GITHUB_KEY", KEY)
    values.put("GITHUB_KEY", KEY + "new")
    values.put("OTHER_KEY", "otherkey1234567")
    values.put("OTHER_KEY", "otherkey7654321")
    retired = values.retired(["GITHUB_KEY"])
    assert len(retired) == 1 and values.values()[retired[0]] == KEY
    values.drop(retired)
    assert KEY not in values.values().values() and values.values()["GITHUB_KEY"] == KEY + "new" and len(values.retired(["OTHER_KEY"])) == 1


def test_a_secret_run_template_with_a_masked_value_or_an_unknown_field_is_refused_and_a_known_field_passes():
    secret = Secret(title="Staging login", fields=({"name": "password", "hidden": True, "variable": "STAGING_PASSWORD"},))
    with pytest.raises(Rejection, match="masked value"):
        SecretRun.check_template(secret, "{[secret STAGING_PASSWORD]}", {"password": KEY})
    with pytest.raises(Rejection, match="no field passwrd"):
        SecretRun.check_template(secret, "{passwrd}", {"password": KEY})
    SecretRun.check_template(secret, "user={password}", {"password": KEY})


@pytest.fixture
def secrets(values: SecretValues, tmp_path):
    from journal.db.connection import Connection
    from journal.db.schema import Schema
    from journal.events.bus import Bus
    from journal.models.all_models import AllModels
    from journal.repositories.secrets import Secrets
    from journal.support.large_reads import LargeReads
    from journal.support.query_times import QueryTimes
    from journal.support.stage_times import StageTimes
    from journal.support.time_source import TimeSource
    connection = Connection(tmp_path / "journal.db", Masks(values), StageTimes(), QueryTimes(), LargeReads())
    Schema(connection, AllModels.MODELS).create()
    yield Secrets(connection, Bus(), TimeSource())
    connection.close()


def test_an_unmasked_text_is_written_as_it_is_and_is_no_leak(values: SecretValues):
    from journal.support.unmasked import Unmasked
    values.write({"GITHUB_KEY": KEY})
    masks = Masks(values)
    assert masks.masked((Unmasked(f"field {KEY}"),)) == (f"field {KEY}",) and type(masks.masked((Unmasked(KEY),))[0]) is str
    assert not masks.has_secret((Unmasked(KEY),)) and masks.leaks == []


def test_a_stored_common_word_is_reported_as_weak_and_never_masks(values: SecretValues):
    values.write({"STAGING_TEST_ACCOUNT_KEY": "password", "GITHUB_KEY": KEY, "SHOWN_USERNAME": "abc"})
    values.write_shown({"SHOWN_USERNAME"})
    masks = Masks(values)
    assert masks.masked(("password",)) == ("password",) and masks.weak == ("STAGING_TEST_ACCOUNT_KEY",)


def test_secret_run_12_stdin_password_resolves_while_another_secret_holds_that_word(values: SecretValues, secrets):
    from journal.support.actor import Actor
    values.write({"STAGING_TEST_ACCOUNT_KEY": "password", "TRACKMIJN_DB_PASSWORD": KEY})
    fields = ({"name": "username", "hidden": False, "variable": "TRACKMIJN_DB_USERNAME"}, {"name": "password", "hidden": True, "variable": "TRACKMIJN_DB_PASSWORD"})
    saved = secrets.save(Secret(title="Trackmijn database", fields=fields, filled=("username", "password")), Actor.user("u"))
    stored = secrets.find(saved.id)
    assert stored.fields == fields and stored.filled == ("username", "password")
    SecretRun.check_template(stored, "{password}", {field["name"]: values.values()[field["variable"]] for field in stored.fields if field["variable"] in values.values()})


def test_a_field_name_is_never_masked_while_the_same_value_in_a_title_is(values: SecretValues, secrets):
    from journal.support.actor import Actor
    values.write({"OTHER_KEY": KEY})
    fields = ({"name": KEY, "hidden": True, "variable": "ODD_TOKEN"},)
    saved = secrets.save(Secret(title=f"odd {KEY}", fields=fields, filled=(KEY,)), Actor.user("u"))
    stored = secrets.find(saved.id)
    assert stored.fields == fields and stored.filled == (KEY,) and stored.title == "odd [secret OTHER_KEY]"


def test_a_field_name_a_mask_rewrote_is_restored_from_its_variable(secrets):
    import json
    from journal.db.migrations.secret_field_names_unmasked import SecretFieldNamesUnmasked
    masked = "[secret STAGING_TEST_ACCOUNT_KEY]"
    rewritten = [{"name": "username", "hidden": False, "variable": "TRACKMIJN_DB_READ_ONLY_USERNAME"}, {"name": masked, "hidden": True, "variable": "TRACKMIJN_DB_READ_ONLY_PASSWORD"}]
    secrets.connection.execute("INSERT INTO secrets (title, fields, filled) VALUES (?, ?, ?)", ("Trackmijn database", json.dumps(rewritten), json.dumps(["username", masked])))
    SecretFieldNamesUnmasked().apply(secrets.connection)
    stored = secrets.all()[0]
    assert [field["name"] for field in stored.fields] == ["username", "password"] and stored.filled == ("username", "password")
