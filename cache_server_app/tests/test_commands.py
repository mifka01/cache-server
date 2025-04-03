#!/usr/bin/env python3.10
"""
test_commands

Module created to test command execution.

Author: Marek Križan
Date: 1.5.2024
"""

import pytest
import os
import shutil
from cache_server_app.src.commands import CacheServerCommandHandler
from cache_server_app.src.agent import Agent
from cache_server_app.src.cache.base import BinaryCache
from cache_server_app.src.workspace import Workspace
from cache_server_app.src.database import CacheServerDatabase

# main fixture for tests
@pytest.fixture()
def setup_fixture():
    # setup
    CacheServerDatabase().create_database()
    setup = {}
    BinaryCache("setupuuid", "setupname", "setupurl", "setuptoken", "public", 0, 0).save()
    os.mkdir("cache_server_app/tests/test_tmp/binary-caches")
    os.mkdir("cache_server_app/tests/test_tmp/binary-caches/setupname")
    setup['cache'] = BinaryCache.get("setupname")
    Workspace("setupuuid", "setupname", "setuptoken", setup['cache']).save()
    setup['workspace'] = Workspace.get("setupname")
    Agent("setupuuid", "setupname", "setuptoken", setup['workspace']).save()
    setup['agent'] = Agent.get("setupname")

    yield setup

    # teardown
    os.remove("cache_server_app/tests/test_tmp/dbfile.db")
    if os.path.exists("cache_server_app/tests/test_tmp/binary-caches"):
        shutil.rmtree("cache_server_app/tests/test_tmp/binary-caches")

#### agent command tests ####

def test_agent_add_correct(setup_fixture) -> None:
    CacheServerCommandHandler().agent_add("testagent", setup_fixture['workspace'].name)

    assert Agent.get('testagent') != None

def test_agent_add_no_workspace(setup_fixture) -> None:
    with pytest.raises(SystemExit) as error:
        CacheServerCommandHandler().agent_add("testagent", "wrong_workspace")

    assert error.value.code == 1

def test_agent_add_exists(setup_fixture) -> None:
    with pytest.raises(SystemExit) as error:
        CacheServerCommandHandler().agent_add(setup_fixture['agent'].name, setup_fixture['workspace'].name)

    assert error.value.code == 1

def test_agent_remove_correct(setup_fixture) -> None:
    name = setup_fixture['agent'].name
    CacheServerCommandHandler().agent_remove(name)

    assert Agent.get(name) == None

def test_agent_remove_not_exist(setup_fixture) -> None:
    with pytest.raises(SystemExit) as error:
        CacheServerCommandHandler().agent_remove("wrong_agent")

    assert error.value.code == 1

#### workspace command tests ####

def test_workspace_create_correct(setup_fixture) -> None:
    CacheServerCommandHandler().workspace_create("testworkspace", setup_fixture['cache'].name)

    assert Workspace.get('testworkspace') != None

def test_workspace_create_no_cache(setup_fixture) -> None:
    with pytest.raises(SystemExit) as error:
        CacheServerCommandHandler().workspace_create("testworkspace", "wrong_cache")

    assert error.value.code == 1

def test_workspace_create_exists(setup_fixture) -> None:
    with pytest.raises(SystemExit) as error:
        CacheServerCommandHandler().workspace_create(setup_fixture['workspace'].name, setup_fixture['cache'].name)

    assert error.value.code == 1

def test_workspace_delete_correct(setup_fixture) -> None:
    name = setup_fixture['workspace'].name
    CacheServerCommandHandler().workspace_delete(name)

    assert Workspace.get(name) == None

def test_workspace_delete_not_exist(setup_fixture) -> None:
    with pytest.raises(SystemExit) as error:
        CacheServerCommandHandler().workspace_delete("wrong_workspace")

    assert error.value.code == 1

#### cache command tests ####

def test_cache_create_correct(setup_fixture) -> None:
    CacheServerCommandHandler().cache_create("testcache", 5000, None)
    cache = BinaryCache.get('testcache')

    assert cache != None
    assert os.path.exists(cache.cache_dir) == True

def test_cache_create_port_exists(setup_fixture) -> None:
    with pytest.raises(SystemExit) as error:
        CacheServerCommandHandler().cache_create("testcache", 0, None)

    assert error.value.code == 1

def test_cache_create_exists(setup_fixture) -> None:
    with pytest.raises(SystemExit) as error:
        CacheServerCommandHandler().cache_create(setup_fixture['cache'].name, 5000, None)

    assert error.value.code == 1

def test_cache_delete_correct(setup_fixture) -> None:
    name = setup_fixture['cache'].name
    CacheServerCommandHandler().workspace_delete(setup_fixture['workspace'].name)
    CacheServerCommandHandler().cache_delete(name)

    assert Workspace.get(name) == None

def test_cache_delete_not_exist(setup_fixture) -> None:
    with pytest.raises(SystemExit) as error:
        CacheServerCommandHandler().cache_delete("wrong_cache")

    assert error.value.code == 1