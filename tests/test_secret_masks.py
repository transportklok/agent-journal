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
